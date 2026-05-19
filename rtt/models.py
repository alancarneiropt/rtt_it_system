import uuid
from decimal import Decimal
from django.db import models
from django.conf import settings
from django.utils import timezone


class Departamento(models.Model):
    """Departamento para agregação de colaboradores e indicadores."""
    nome = models.CharField(max_length=120)
    ativo = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Departamento'
        verbose_name_plural = 'Departamentos'
        ordering = ['nome']

    def __str__(self):
        return self.nome


class Jornada(models.Model):
    """Jornada de trabalho (escala): horários planejados e tipo (comercial, 12x36, noturno)."""
    TIPO_CHOICES = [
        ('padrao', 'Padrão (08h-18h)'),
        ('comercial', 'Comercial'),
        ('12x36', '12x36'),
        ('noturno', 'Noturno'),
        ('flexivel', 'Flexível'),
    ]
    nome = models.CharField(max_length=80, help_text='Ex: Vendas 08h-18h')
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default='padrao')
    hora_entrada_planejada = models.TimeField(default='08:00', help_text='Entrada planejada')
    hora_saida_planejada = models.TimeField(default='18:00', help_text='Saída planejada')
    hora_inicio_intervalo = models.TimeField(default='12:00', null=True, blank=True)
    hora_fim_intervalo = models.TimeField(default='13:00', null=True, blank=True)
    ativo = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Jornada'
        verbose_name_plural = 'Jornadas'
        ordering = ['nome']

    def __str__(self):
        return self.nome


class Profile(models.Model):
    """Perfil do colaborador: nome, endereço, data nascimento, departamento e jornada."""
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='profile'
    )
    nome = models.CharField(max_length=255, unique=True)
    endereco = models.CharField(max_length=500, blank=True)
    data_nascimento = models.DateField(null=True, blank=True)
    departamento = models.ForeignKey(
        Departamento,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='colaboradores'
    )
    jornada = models.ForeignKey(
        Jornada,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='colaboradores'
    )
    viatura = models.ForeignKey(
        'Viatura',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='colaboradores'
    )
    cartao = models.ForeignKey(
        'Cartao',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='colaboradores'
    )

    class Meta:
        verbose_name = 'Perfil'
        verbose_name_plural = 'Perfis'

    def __str__(self):
        return self.nome or self.user.email or str(self.user.pk)

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        old_viatura = None
        old_cartao = None
        
        if not is_new:
            try:
                old_profile = Profile.objects.get(pk=self.pk)
                old_viatura = old_profile.viatura
                old_cartao = old_profile.cartao
            except Profile.DoesNotExist:
                pass
                
        super().save(*args, **kwargs)
        
        from django.utils import timezone
        
        # Sincronizar viatura
        if old_viatura != self.viatura:
            if old_viatura:
                ViaturaHistoricoAtribuicao.objects.filter(
                    viatura=old_viatura,
                    colaborador=self.user,
                    data_remocao__isnull=True
                ).update(data_remocao=timezone.now())
                
                if old_viatura.colaborador_atual == self.user:
                    old_viatura.colaborador_atual = None
                    old_viatura.save(update_fields=['colaborador_atual'])
                    
            if self.viatura:
                ViaturaHistoricoAtribuicao.objects.filter(
                    viatura=self.viatura,
                    data_remocao__isnull=True
                ).update(data_remocao=timezone.now())
                
                ViaturaHistoricoAtribuicao.objects.get_or_create(
                    viatura=self.viatura,
                    colaborador=self.user,
                    data_remocao__isnull=True,
                    defaults={'data_atribuicao': timezone.now()}
                )
                
                if self.viatura.colaborador_atual != self.user:
                    self.viatura.colaborador_atual = self.user
                    self.viatura.save(update_fields=['colaborador_atual'])
                    
        # Sincronizar cartão
        if old_cartao != self.cartao:
            if old_cartao:
                CartaoHistoricoAtribuicao.objects.filter(
                    cartao=old_cartao,
                    colaborador=self.user,
                    data_remocao__isnull=True
                ).update(data_remocao=timezone.now())
                
                if old_cartao.colaborador_atual == self.user:
                    old_cartao.colaborador_atual = None
                    old_cartao.save(update_fields=['colaborador_atual'])
                    
            if self.cartao:
                CartaoHistoricoAtribuicao.objects.filter(
                    cartao=self.cartao,
                    data_remocao__isnull=True
                ).update(data_remocao=timezone.now())
                
                CartaoHistoricoAtribuicao.objects.get_or_create(
                    cartao=self.cartao,
                    colaborador=self.user,
                    data_remocao__isnull=True,
                    defaults={'data_atribuicao': timezone.now()}
                )
                
                if self.cartao.colaborador_atual != self.user:
                    self.cartao.colaborador_atual = self.user
                    self.cartao.save(update_fields=['colaborador_atual'])


class Marcacao(models.Model):
    """Registo de presença com localização, tipo e estado de aprovação."""
    TIPO_CHOICES = [
        ('entrada', 'Entrada'),
        ('saida', 'Saída'),
    ]

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    utilizador = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='marcacoes'
    )
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    timestamp = models.DateTimeField(default=timezone.now)
    aprovado = models.BooleanField(default=False)
    aprovado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='marcacoes_aprovadas'
    )
    aprovado_em = models.DateTimeField(null=True, blank=True)
    justificativa = models.TextField(
        blank=True,
        help_text='Obrigatório ao marcar saída sem ter registado pausa para almoço.'
    )

    class Meta:
        verbose_name = 'Marcação'
        verbose_name_plural = 'Marcações'
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.utilizador} - {self.get_tipo_display()} ({self.timestamp})"


class Viatura(models.Model):
    """Cadastro de viaturas da empresa."""
    matricula = models.CharField(max_length=20, unique=True)
    marca_modelo = models.CharField(max_length=100, blank=True)
    km_inicial = models.IntegerField(default=0, help_text="KM no momento do cadastro no sistema")
    km_atual = models.IntegerField(default=0, help_text="KM atualizado automaticamente")
    ativo = models.BooleanField(default=True)
    colaborador_atual = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='viaturas_atuais'
    )

    class Meta:
        verbose_name = 'Viatura'
        verbose_name_plural = 'Viaturas'

    def __str__(self):
        return f"{self.matricula} ({self.km_atual} KM)"

    @property
    def km_percorrido(self):
        return (self.km_atual or 0) - (self.km_inicial or 0)

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        old_colab = None
        
        if not is_new:
            try:
                old_viatura = Viatura.objects.get(pk=self.pk)
                old_colab = old_viatura.colaborador_atual
            except Viatura.DoesNotExist:
                pass
                
        if not is_new:
            # Garante que o KM atual nunca seja inferior ao inicial (correção de erro de digitação)
            if self.km_atual < self.km_inicial:
                self.km_atual = self.km_inicial
        else:
            # No primeiro cadastro, o km_atual segue o km_inicial
            if not self.km_atual:
                self.km_atual = self.km_inicial
                
        super().save(*args, **kwargs)
        
        # Se mudou o colaborador_atual
        if old_colab != self.colaborador_atual:
            from django.utils import timezone
            # 1. Fechar atribuição antiga
            if old_colab:
                ViaturaHistoricoAtribuicao.objects.filter(
                    viatura=self,
                    colaborador=old_colab,
                    data_remocao__isnull=True
                ).update(data_remocao=timezone.now())
                
                # Desassociar no perfil do utilizador antigo
                if hasattr(old_colab, 'profile') and old_colab.profile.viatura == self:
                    old_colab.profile.viatura = None
                    old_colab.profile.save(update_fields=['viatura'])
                    
            # 2. Criar nova atribuição
            if self.colaborador_atual:
                # Fechar qualquer outra ativa desta viatura
                ViaturaHistoricoAtribuicao.objects.filter(
                    viatura=self,
                    data_remocao__isnull=True
                ).update(data_remocao=timezone.now())
                
                ViaturaHistoricoAtribuicao.objects.create(
                    viatura=self,
                    colaborador=self.colaborador_atual,
                    data_atribuicao=timezone.now()
                )
                
                # Associar no perfil do novo utilizador
                if hasattr(self.colaborador_atual, 'profile') and self.colaborador_atual.profile.viatura != self:
                    self.colaborador_atual.profile.viatura = self
                    self.colaborador_atual.profile.save(update_fields=['viatura'])

    def get_ultimo_registo(self):
        """Retorna o último registo de KM desta viatura."""
        return self.registos.order_by('-timestamp').first()


class Cartao(models.Model):
    """Cadastro de cartões de abastecimento da empresa."""
    nome = models.CharField(max_length=100, blank=True, help_text="Identificação do cartão (ex: Galp Frota)")
    numero = models.CharField(max_length=50, unique=True, help_text="Número completo do cartão")
    ativo = models.BooleanField(default=True)
    colaborador_atual = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='cartoes_atuais'
    )

    class Meta:
        verbose_name = 'Cartão de Combustível'
        verbose_name_plural = 'Cartões de Combustível'

    def __str__(self):
        return f"{self.nome} ({self.numero})"

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        old_colab = None
        
        if not is_new:
            try:
                old_cartao = Cartao.objects.get(pk=self.pk)
                old_colab = old_cartao.colaborador_atual
            except Cartao.DoesNotExist:
                pass
                
        super().save(*args, **kwargs)
        
        # Se mudou o colaborador_atual
        if old_colab != self.colaborador_atual:
            from django.utils import timezone
            # 1. Fechar atribuição antiga
            if old_colab:
                CartaoHistoricoAtribuicao.objects.filter(
                    cartao=self,
                    colaborador=old_colab,
                    data_remocao__isnull=True
                ).update(data_remocao=timezone.now())
                
                # Desassociar no perfil do utilizador antigo
                if hasattr(old_colab, 'profile') and old_colab.profile.cartao == self:
                    old_colab.profile.cartao = None
                    old_colab.profile.save(update_fields=['cartao'])
                    
            # 2. Criar nova atribuição
            if self.colaborador_atual:
                # Fechar qualquer outra ativa deste cartão
                CartaoHistoricoAtribuicao.objects.filter(
                    cartao=self,
                    data_remocao__isnull=True
                ).update(data_remocao=timezone.now())
                
                CartaoHistoricoAtribuicao.objects.create(
                    cartao=self,
                    colaborador=self.colaborador_atual,
                    data_atribuicao=timezone.now()
                )
                
                # Associar no perfil do novo utilizador
                if hasattr(self.colaborador_atual, 'profile') and self.colaborador_atual.profile.cartao != self:
                    self.colaborador_atual.profile.cartao = self
                    self.colaborador_atual.profile.save(update_fields=['cartao'])


class RegistroKM(models.Model):
    """Registo de quilometragem: permite múltiplos registos por dia (tipo histórico)."""
    utilizador = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='registos_km'
    )
    data = models.DateField(auto_now_add=True)
    timestamp = models.DateTimeField(default=timezone.now)
    km = models.IntegerField(default=0, help_text="Valor do KM no momento")
    km_anterior = models.IntegerField(default=0, help_text="Valor do KM antes deste registo")
    viatura = models.ForeignKey(Viatura, on_delete=models.SET_NULL, null=True, blank=True, related_name='registos')

    class Meta:
        verbose_name = 'Registo de KM'
        verbose_name_plural = 'Registos de KM'
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.utilizador} - {self.km} KM ({self.timestamp.strftime('%d/%m %H:%M')})"
    
    @property
    def distancia(self):
        return self.km - self.km_anterior

    @property
    def distancia_percorrida(self):
        # Para lógica de histórico, o percorrido seria o KM atual menos o KM anterior do mesmo utilizador
        # Mas para simplificar, se for só um log, o cálculo de distância pode ser feito via query
        return None


class Abastecimento(models.Model):
    STATUS_CHOICES = [
        ('pendente', 'Pendente de Aprovação'),
        ('aprovado', 'Aprovado'),
        ('rejeitado', 'Rejeitado'),
    ]

    utilizador = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='abastecimentos'
    )
    viatura = models.ForeignKey(
        Viatura, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='abastecimentos'
    )
    timestamp = models.DateTimeField(default=timezone.now)
    data = models.DateField(auto_now_add=True)
    km = models.IntegerField(help_text="KM no momento do abastecimento")
    valor = models.DecimalField(max_digits=8, decimal_places=2, help_text="Valor gasto (€)")
    litros = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True, help_text="Litros abastecidos")
    comprovativo = models.FileField(upload_to='comprovativos_abastecimento/', null=True, blank=True)
    comprovativo_texto_ocr = models.TextField(blank=True, help_text="Texto extraído por OCR da fatura/recibo")
    metodo_pagamento = models.CharField(max_length=20, choices=[('dinheiro', 'Dinheiro (€)'), ('cartao', 'Cartão')], default='dinheiro')
    cartao = models.CharField(max_length=100, blank=True, null=True, help_text="Nº do cartão utilizado")
    cartao_ref = models.ForeignKey('Cartao', on_delete=models.SET_NULL, null=True, blank=True, related_name='abastecimentos')
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pendente')
    aprovado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='abastecimentos_aprovados'
    )
    aprovado_em = models.DateTimeField(null=True, blank=True)
    justificativa_admin = models.TextField(blank=True, help_text="Observações da aprovação/rejeição")

    class Meta:
        verbose_name = 'Abastecimento de Combustível'
        verbose_name_plural = 'Abastecimentos de Combustível'
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.utilizador} - €{self.valor} ({self.timestamp.strftime('%d/%m/%Y')})"


class ViaturaHistoricoAtribuicao(models.Model):
    """Histórico de atribuição de viaturas a colaboradores."""
    viatura = models.ForeignKey('Viatura', on_delete=models.CASCADE, related_name='historico_atribuicoes')
    colaborador = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='historico_viaturas')
    data_atribuicao = models.DateTimeField(default=timezone.now)
    data_remocao = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Histórico de Atribuição de Viatura'
        verbose_name_plural = 'Históricos de Atribuições de Viaturas'
        ordering = ['-data_atribuicao']

    def __str__(self):
        status = f"até {self.data_remocao.strftime('%d/%m/%Y %H:%M')}" if self.data_remocao else "Ativo"
        return f"{self.viatura.matricula} -> {self.colaborador.email} ({status})"


class CartaoHistoricoAtribuicao(models.Model):
    """Histórico de atribuição de cartões de combustível a colaboradores."""
    cartao = models.ForeignKey('Cartao', on_delete=models.CASCADE, related_name='historico_atribuicoes')
    colaborador = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='historico_cartoes')
    data_atribuicao = models.DateTimeField(default=timezone.now)
    data_remocao = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Histórico de Atribuição de Cartão'
        verbose_name_plural = 'Históricos de Atribuições de Cartões'
        ordering = ['-data_atribuicao']

    def __str__(self):
        status = f"até {self.data_remocao.strftime('%d/%m/%Y %H:%M')}" if self.data_remocao else "Ativo"
        return f"{self.cartao.nome} -> {self.colaborador.email} ({status})"
