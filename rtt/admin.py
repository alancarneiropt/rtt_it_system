from django.contrib import admin
from django.utils.html import format_html
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth import get_user_model
from .models import Profile, Marcacao, Departamento, Jornada

User = get_user_model()

# Substituir o User admin padrão pelo nosso (com perfil e nome)
if User in admin.site._registry:
    admin.site.unregister(User)


@admin.register(Departamento)
class DepartamentoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'ativo')
    list_editable = ('ativo',)
    search_fields = ('nome',)


@admin.register(Jornada)
class JornadaAdmin(admin.ModelAdmin):
    list_display = ('nome', 'tipo', 'hora_entrada_planejada', 'hora_saida_planejada', 'hora_inicio_intervalo', 'hora_fim_intervalo', 'ativo')
    list_editable = ('hora_entrada_planejada', 'hora_saida_planejada', 'hora_inicio_intervalo', 'hora_fim_intervalo', 'ativo')
    list_filter = ('tipo', 'ativo')
    search_fields = ('nome',)


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('nome', 'user', 'email_do_user', 'departamento', 'jornada', 'data_nascimento')
    list_editable = ('departamento', 'jornada')
    list_filter = ('departamento', 'jornada')
    search_fields = ('nome', 'user__email')
    raw_id_fields = ('user',)
    fieldsets = (
        (None, {'fields': ('user', 'nome', 'endereco', 'data_nascimento')}),
        ('Trabalho', {'fields': ('departamento', 'jornada')}),
    )

    def email_do_user(self, obj):
        return obj.user.email if obj.user_id else '-'
    email_do_user.short_description = 'Email'


class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name_plural = 'Perfil'
    fk_name = 'user'
    autocomplete_fields = ('departamento', 'jornada',)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    inlines = (ProfileInline,)
    list_display = ('email', 'username', 'nome_perfil', 'is_staff', 'is_active', 'date_joined')
    list_filter = ('is_staff', 'is_active')
    search_fields = ('email', 'username')
    ordering = ('-date_joined',)

    def nome_perfil(self, obj):
        try:
            return obj.profile.nome
        except Profile.DoesNotExist:
            return '-'
    nome_perfil.short_description = 'Nome'


@admin.register(Marcacao)
class MarcacaoAdmin(admin.ModelAdmin):
    list_display = ('utilizador', 'tipo', 'data_hora', 'aprovado', 'localizacao', 'link_mapa')
    list_filter = ('tipo', 'utilizador', 'aprovado')
    search_fields = ('utilizador__email',)
    readonly_fields = ('id', 'timestamp', 'link_mapa')
    date_hierarchy = 'timestamp'
    list_editable = ('aprovado',)

    def data_hora(self, obj):
        from django.utils import timezone
        return timezone.localtime(obj.timestamp).strftime('%Y-%m-%d %H:%M:%S') if obj.timestamp else '-'
    data_hora.short_description = 'Data/Hora'
    data_hora.admin_order_field = 'timestamp'

    def localizacao(self, obj):
        return f'{obj.latitude}, {obj.longitude}'
    localizacao.short_description = 'Localização'

    def link_mapa(self, obj):
        if obj.latitude and obj.longitude and (obj.latitude != 0 or obj.longitude != 0):
            return format_html(
                '<a href="https://www.google.com/maps?q={},{}" target="_blank" rel="noopener">Ver no mapa</a>',
                obj.latitude, obj.longitude
            )
        return '-'
    link_mapa.short_description = 'Mapa'
