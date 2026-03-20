"""
Backend de autenticação por email e palavra-passe.
"""
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model

User = get_user_model()


class EmailAuthBackend(ModelBackend):
    """Permite login via email e palavra-passe."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        email = kwargs.get('email') or username
        if not email or not password:
            return None
        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            return None
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
