from django.urls import path
from . import backoffice_views

urlpatterns = [
    path('login/', backoffice_views.backoffice_login_view, name='backoffice_login'),
    path('logout/', backoffice_views.backoffice_logout_view, name='backoffice_logout'),
    path('', backoffice_views.dashboard_espelho_view, name='backoffice_dashboard'),
    path('espelho/', backoffice_views.dashboard_espelho_view, name='backoffice_espelho'),
    path('indicadores/', backoffice_views.indicadores_view, name='backoffice_indicadores'),
    path('departamentos/', backoffice_views.departamento_list_view, name='backoffice_departamento_list'),
    path('departamentos/novo/', backoffice_views.departamento_create_view, name='backoffice_departamento_create'),
    path('departamentos/<int:pk>/editar/', backoffice_views.departamento_edit_view, name='backoffice_departamento_edit'),
    path('jornadas/', backoffice_views.jornada_list_view, name='backoffice_jornada_list'),
    path('jornadas/novo/', backoffice_views.jornada_create_view, name='backoffice_jornada_create'),
    path('jornadas/<int:pk>/editar/', backoffice_views.jornada_edit_view, name='backoffice_jornada_edit'),
    path('colaboradores/', backoffice_views.colaborador_list_view, name='backoffice_colaborador_list'),
    path('colaboradores/novo/', backoffice_views.colaborador_create_view, name='backoffice_colaborador_create'),
    path('colaboradores/<int:pk>/', backoffice_views.colaborador_detail_view, name='backoffice_colaborador_detail'),
    path('colaboradores/<int:pk>/editar/', backoffice_views.colaborador_edit_view, name='backoffice_colaborador_edit'),
    path('api/aprovar-ponto/', backoffice_views.aprovar_ponto_view, name='backoffice_aprovar_ponto'),
    path('api/adicionar-ponto/', backoffice_views.adicionar_ponto_view, name='backoffice_adicionar_ponto'),
    path('export/excel/', backoffice_views.export_espelho_excel_view, name='backoffice_export_excel'),
    path('export/pdf/', backoffice_views.export_espelho_pdf_view, name='backoffice_export_pdf'),
    path('km-registros/', backoffice_views.backoffice_km_list_view, name='backoffice_km_list'),
    path('km-registros/novo/', backoffice_views.backoffice_km_create_view, name='backoffice_km_create'),
    path('km-registros/<int:pk>/eliminar/', backoffice_views.backoffice_km_delete_view, name='backoffice_km_delete'),
    path('viaturas/', backoffice_views.viatura_list_view, name='backoffice_viatura_list'),
    path('viaturas/novo/', backoffice_views.viatura_create_view, name='backoffice_viatura_create'),
    path('viaturas/<int:pk>/editar/', backoffice_views.viatura_edit_view, name='backoffice_viatura_edit'),
    path('cartoes/', backoffice_views.cartao_list_view, name='backoffice_cartao_list'),
    path('cartoes/novo/', backoffice_views.cartao_create_view, name='backoffice_cartao_create'),
    path('cartoes/<int:pk>/editar/', backoffice_views.cartao_edit_view, name='backoffice_cartao_edit'),
    path('colaboradores/ponto/<uuid:pk>/editar/', backoffice_views.ponto_edit_view, name='backoffice_ponto_edit'),
    path('colaboradores/ponto/<uuid:pk>/excluir/', backoffice_views.ponto_delete_view, name='backoffice_ponto_delete'),
    
    # Gestão de Combustível / Abastecimentos
    path('abastecimentos/', backoffice_views.backoffice_abastecimento_list_view, name='backoffice_abastecimento_list'),
    path('abastecimentos/<int:pk>/aprovar/', backoffice_views.backoffice_abastecimento_aprovar_view, name='backoffice_abastecimento_aprovar'),
    path('abastecimentos/<int:pk>/rejeitar/', backoffice_views.backoffice_abastecimento_rejeitar_view, name='backoffice_abastecimento_rejeitar'),
    
    # Histórico e Auditoria
    path('historico/', backoffice_views.backoffice_historico_view, name='backoffice_historico'),
    path('historico/export/excel/', backoffice_views.export_historico_excel_view, name='backoffice_historico_export_excel'),
    path('historico/export/pdf/', backoffice_views.export_historico_pdf_view, name='backoffice_historico_export_pdf'),
]
