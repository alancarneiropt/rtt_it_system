import django, os, sys
sys.path.insert(0, r'c:\Users\Ielber.Silva\Desktop\rtt_it_system')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'rtt_it_system.settings')
django.setup()

from django.contrib.auth.models import User
from rtt.models import Profile, Viatura, Cartao

EMAIL = 'ielber.silva@ica.pt'

print("=" * 60)
print("DIAGNOSTICO: UTILIZADORES COM EMAIL", EMAIL)
print("=" * 60)

users = list(User.objects.filter(email__iexact=EMAIL))
print(f"Total de utilizadores encontrados: {len(users)}\n")

for u in users:
    print(f"  ID={u.pk} | username='{u.username}' | email='{u.email}'")
    print(f"    is_staff={u.is_staff} | is_active={u.is_active} | is_superuser={u.is_superuser}")
    try:
        p = u.profile
        print(f"    PERFIL: nome='{p.nome}' | viatura={p.viatura} | cartao={p.cartao}")
    except:
        print(f"    SEM PERFIL")
    print()

if len(users) < 2:
    print("Nao ha duplicados. A verificar o perfil...")
elif len(users) >= 2:
    print("=" * 60)
    print("A RESOLVER DUPLICADOS...")
    print("=" * 60)

    # Encontrar o utilizador principal (com perfil e nome correcto)
    principal = None
    duplicados = []
    
    for u in users:
        try:
            p = u.profile
            if p.nome and p.nome != EMAIL and p.nome.strip():
                principal = u
            else:
                duplicados.append(u)
        except:
            duplicados.append(u)
    
    # Se nenhum tem perfil com nome, pega o que tem is_staff
    if not principal:
        for u in users:
            if u.is_staff:
                principal = u
                break
    
    # Se ainda nao temos principal, pega o de menor ID
    if not principal:
        principal = min(users, key=lambda x: x.pk)
        duplicados = [u for u in users if u.pk != principal.pk]
    else:
        duplicados = [u for u in users if u.pk != principal.pk]
    
    print(f"Utilizador PRINCIPAL: ID={principal.pk} | '{principal.username}'")
    for d in duplicados:
        print(f"Utilizador DUPLICADO: ID={d.pk} | '{d.username}'")
    
    # Garantir que o principal tem os dados correctos
    principal.is_staff = True
    principal.is_superuser = False  # Apenas staff, nao superuser
    
    # Garantir password admin123
    if not principal.check_password('admin123'):
        print("  A definir password admin123...")
        principal.set_password('admin123')
    
    principal.save()
    print(f"  Principal guardado.")
    
    # Corrigir o perfil do principal
    try:
        p = principal.profile
        if not p.nome or p.nome.strip() == '' or p.nome == EMAIL:
            p.nome = 'ielber Veiga Pellegrini Da Silva'
            print(f"  A corrigir nome do perfil...")
        
        # Garantir viatura associada
        viatura = Viatura.objects.filter(matricula='TE-00-ST').first()
        if viatura and p.viatura != viatura:
            p.viatura = viatura
            print(f"  A re-associar viatura TE-00-ST...")
        
        p.save(update_fields=['nome', 'viatura', 'cartao'])
        
        # Garantir Viatura.colaborador_atual
        if viatura and viatura.colaborador_atual != principal:
            viatura.colaborador_atual = principal
            viatura.save(update_fields=['colaborador_atual'])
            print(f"  A actualizar Viatura.colaborador_atual...")
            
        print(f"  Perfil corrigido!")
    except Exception as e:
        print(f"  ERRO no perfil: {e}")
    
    # Eliminar duplicados
    for d in duplicados:
        print(f"\n  A eliminar duplicado ID={d.pk}...")
        try:
            # Primeiro eliminar o perfil se existir
            try:
                d.profile.delete()
                print(f"    Perfil eliminado.")
            except:
                pass
            d.delete()
            print(f"    Utilizador eliminado.")
        except Exception as e:
            print(f"    ERRO ao eliminar: {e}")

print("\n" + "=" * 60)
print("ESTADO FINAL")
print("=" * 60)
users_final = list(User.objects.filter(email__iexact=EMAIL))
print(f"Utilizadores com email {EMAIL}: {len(users_final)}")
for u in users_final:
    print(f"  ID={u.pk} | is_staff={u.is_staff} | pw_ok={u.check_password('admin123')}")
    try:
        p = u.profile
        print(f"  Perfil: nome='{p.nome}' | viatura={p.viatura} | cartao={p.cartao}")
    except:
        print(f"  SEM PERFIL")
print("\nConcluido!")
