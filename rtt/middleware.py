"""
Middleware para separar a sessão do backoffice da sessão da app.
Assim, um admin logado no backoffice e um utilizador logado na app
podem coexistir (como dois sites independentes).
"""
from django.conf import settings

BACKOFFICE_SESSION_COOKIE_NAME = 'backoffice_sessionid'
BACKOFFICE_PATH_PREFIX = '/backoffice/'


class BackofficeSessionMiddleware:
    """
    Para pedidos sob /backoffice/, usa um cookie de sessão diferente.
    O SessionMiddleware (que corre a seguir) usa settings.SESSION_COOKIE_NAME,
    por isso alteramos esse setting temporariamente para que a sessão do
    backoffice fique totalmente separada da sessão da app.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith(BACKOFFICE_PATH_PREFIX):
            request._backoffice_session = True
            self._original_cookie_name = getattr(settings, 'SESSION_COOKIE_NAME', 'sessionid')
            settings.SESSION_COOKIE_NAME = BACKOFFICE_SESSION_COOKIE_NAME
        else:
            request._backoffice_session = False

        response = self.get_response(request)

        if getattr(request, '_backoffice_session', False):
            settings.SESSION_COOKIE_NAME = self._original_cookie_name

        return response
