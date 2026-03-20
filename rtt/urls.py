from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('marcacoes/', views.marcacao_list_create, name='marcacao_list_create'),
    path('marcacoes/minhas/', views.minhas_marcacoes, name='minhas_marcacoes'),
    path('utilizadores/', views.utilizador_create, name='utilizador_create'),
    path('relatorios/marcacoes/', views.relatorios_marcacoes, name='relatorios_marcacoes'),
    path('relatorios/exportar_csv/', views.relatorios_exportar_csv, name='relatorios_exportar_csv'),
]
