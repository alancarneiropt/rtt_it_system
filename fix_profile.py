"""
Script de correção: restaura o nome do perfil de ielber.silva@ica.pt
e verifica o estado actual da conta.
Execute na pasta do projecto:
  .venv\Scripts\python.exe fix_profile.py
"""
import django, os, sys
sys.path.insert(0, r'c:\Users\Ielber.Silva\Desktop\rtt_it_system')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'rtt_it_system.settings')
django.setup()

from django.contrib.auth.models import User
from rtt.models import Profile

EMAIL = 'ielber.silva@ica.pt'
NOME_CORRETO = 'ielber Veiga Pellegrini Da Silva'

try:
    u = User.objects.get(email=EMAIL)
    print(f'Utilizador encontrado: {u.email}')
    print(f'  is_staff: {u.is_staff}')
    print(f'  is_active: {u.is_active}')
    print(f'  Password check (admin123): {u.check_password("admin123")}')
    
    try:
        p = u.profile
        print(f'\nPerfil encontrado:')
        print(f'  nome actual: "{p.nome}"')
        print(f'  viatura: {p.viatura}')
        print(f'  cartao: {p.cartao}')
        
        if not p.nome or p.nome.strip() == '':
            print(f'\n⚠️  Nome está vazio! A corrigir para: "{NOME_CORRETO}"')
            p.nome = NOME_CORRETO
            p.save(update_fields=['nome'])
            print('✅ Nome corrigido com sucesso!')
        else:
            print(f'\n✅ Nome está correcto: "{p.nome}"')
            
    except Profile.DoesNotExist:
        print('\n❌ ERRO: Perfil não encontrado para este utilizador!')
        
except User.DoesNotExist:
    print(f'❌ ERRO: Utilizador {EMAIL} não encontrado!')
except Exception as e:
    print(f'❌ ERRO inesperado: {e}')
    import traceback
    traceback.print_exc()
