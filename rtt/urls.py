from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('hora-servidor/', views.hora_servidor, name='hora_servidor'),
    path('marcacoes/', views.marcacao_list_create, name='marcacao_list_create'),
    path('marcacoes/minhas/', views.minhas_marcacoes, name='minhas_marcacoes'),
    path('utilizadores/', views.utilizador_create, name='utilizador_create'),
    path('relatorios/marcacoes/', views.relatorios_marcacoes, name='relatorios_marcacoes'),
    path('relatorios/exportar_csv/', views.relatorios_exportar_csv, name='relatorios_exportar_csv'),
    path('km-registo/', views.km_registo_view, name='km_registo'),
    path('km-status/', views.km_status_view, name='km_status'),
    path('km-registos-todos/', views.km_registos_todos_view, name='km_registos_todos'),
    path('km-historico/', views.km_historico_view, name='km_historico'),
    path('viaturas-api/', views.viaturas_api_view, name='viaturas_api'),
    path('abastecimento/registar/', views.abastecimento_registar_view, name='abastecimento_registar'),
    path('abastecimento/minhas/', views.abastecimento_minhas_view, name='abastecimento_minhas'),
    path('abastecimento/ocr/', views.abastecimento_ocr_view, name='abastecimento_ocr'),
]
