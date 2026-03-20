# Filtros para o backoffice (espelho de ponto e relatórios)
import django_filters
from django.contrib.auth import get_user_model
from .models import Marcacao

User = get_user_model()


class EspelhoPontoFilter(django_filters.FilterSet):
    """Filtros para o dashboard espelho de ponto."""
    colaborador = django_filters.ModelChoiceFilter(
        queryset=User.objects.filter(profile__isnull=False).distinct(),
        field_name='utilizador',
        label='Colaborador',
    )
    data_inicio = django_filters.DateFilter(
        field_name='timestamp',
        lookup_expr='date__gte',
        label='Data início',
    )
    data_fim = django_filters.DateFilter(
        field_name='timestamp',
        lookup_expr='date__lte',
        label='Data fim',
    )
    aprovado = django_filters.BooleanFilter(
        field_name='aprovado',
        label='Aprovado',
    )
