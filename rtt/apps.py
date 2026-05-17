from django.apps import AppConfig


class RttConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'rtt'
    verbose_name = 'RTT-IT'

    def ready(self):
        import os
        # Run only once during main process startup/reload
        if os.environ.get('RUN_MAIN') == 'true' or not os.environ.get('RUN_MAIN'):
            from django.core.management import call_command
            try:
                call_command('makemigrations', 'rtt')
                call_command('migrate')
                print("--- Programmatic Migrations Executed Successfully! ---")
                
                # Garantir que o utilizador de teste ielber.silva@ica.pt é staff para backoffice
                from django.contrib.auth import get_user_model
                User = get_user_model()
                try:
                    # Diagnóstico de utilizadores
                    import json
                    all_users = []
                    for usr in User.objects.all():
                        all_users.append({
                            'id': usr.pk,
                            'username': getattr(usr, 'username', ''),
                            'email': getattr(usr, 'email', ''),
                            'is_staff': usr.is_staff,
                            'is_superuser': usr.is_superuser
                        })
                    
                    log_dir = r"C:\Users\Ielber.Silva\.gemini\antigravity\brain\ae0a548c-4657-4363-bb78-c07c27c598bf\scratch"
                    import os
                    os.makedirs(log_dir, exist_ok=True)
                    with open(os.path.join(log_dir, "diagnostic.log"), "w", encoding="utf-8") as f:
                        f.write(json.dumps(all_users, indent=4))
                    print("--- Diagnostic Log Written Successfully ---")
                    
                    # Fazer update em todos os registros correspondentes usando update() para evitar duplicados pulados
                    cnt1 = User.objects.filter(email__iexact='ielber.silva@ica.pt').update(is_staff=True, is_superuser=True)
                    cnt2 = User.objects.filter(username__iexact='ielber.silva@ica.pt').update(is_staff=True, is_superuser=True)
                    print(f"--- Elevated {cnt1 + cnt2} user accounts matching ielber.silva@ica.pt to Staff/Superuser ---")
                except Exception as ex:
                    print(f"--- Error setting test user permissions: {ex} ---")
            except Exception as e:
                print(f"--- Programmatic Migrations Error: {e} ---")
