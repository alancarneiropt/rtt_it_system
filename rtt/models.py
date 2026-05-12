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

    class Meta:
        verbose_name = 'Perfil'
        verbose_name_plural = 'Perfis'

    def __str__(self):
        return self.nome or self.user.email or str(self.user.pk)


class Marcacao(models.Model):
    """Registo de presença com localização, tipo e estado de aprovação."""
    TIPO_CHOICES = [
        ('entrada', 'Entrada'),
        ('inicio_almoco', 'Início Almoço'),
        ('fim_almoco', 'Fim Almoço'),
        ('fim_jornada', 'Fim Jornada'),
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
    timestamp = models.DateTimeField(auto_now_add=True)
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

    class Meta:
        verbose_name = 'Viatura'
        verbose_name_plural = 'Viaturas'

    def __str__(self):
        return f"{self.matricula} ({self.km_atual} KM)"

    def save(self, *args, **kwargs):
        if not self.pk:
            # No primeiro cadastro, o km_atual é o km_inicial
            self.km_atual = self.km_inicial
        super().save(*args, **kwargs)


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
    descricao = models.CharField(max_length=255, blank=True, help_text="Onde estou / observações")

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
