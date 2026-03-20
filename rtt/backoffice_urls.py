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
]
