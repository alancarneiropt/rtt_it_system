import django, os, sys
sys.path.insert(0, r'c:\Users\Ielber.Silva\Desktop\rtt_it_system')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'rtt_it_system.settings')
django.setup()

from django.contrib.auth.models import User

try:
    u = User.objects.get(email='ielber.silva@ica.pt')
    print('=== ESTADO DO UTILIZADOR ===')
    print(f'Email: {u.email}')
    print(f'Is staff: {u.is_staff}')
    print(f'Is active: {u.is_active}')
    print(f'Password check (admin123): {u.check_password("admin123")}')
    
    p = u.profile
    print(f'\n=== PERFIL ===')
    print(f'Nome: {p.nome}')
    print(f'Viatura: {p.viatura}')
    print(f'Cartao: {p.cartao}')
    print(f'Departamento: {p.departamento}')
    print(f'Jornada: {p.jornada}')
    
except User.DoesNotExist:
    print('ERRO: Utilizador nao encontrado!')
except Exception as e:
    print(f'ERRO: {e}')
