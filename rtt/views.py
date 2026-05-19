import csv
from decimal import Decimal, InvalidOperation
from django.contrib.auth import authenticate, login, get_user_model
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.utils import timezone

from django.views.decorators.http import require_GET, require_POST
from django.views.decorators.cache import never_cache
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import logout as auth_logout
import json

from .models import Marcacao, Profile, RegistroKM, Viatura

User = get_user_model()


@require_GET
@never_cache
def health_view(request):
    """Healthcheck para Docker / balanceador (sem consulta à BD)."""
    return HttpResponse('OK', content_type='text/plain; charset=utf-8')


# ---------- Página inicial: sempre tela de login ----------
def root_view(request):
    """
    Raiz (/) unificada:
    - Se não logado: mostra tela de login única.
    - Se logado e admin (is_staff): vai para o dashboard do backoffice.
    - Se logado e comum: vai para a área do utilizador.
    """
    if request.user.is_authenticated:
        if request.user.is_staff:
            return redirect('backoffice_dashboard')
        return redirect('area_utilizador')

    if request.method == 'POST':
        email = (request.POST.get('email') or '').strip()
        palavra_passe = request.POST.get('palavra_passe') or ''
        
        if not email or not palavra_passe:
            return render(request, 'rtt/login.html', {'erro': 'Indique email e palavra-passe.', 'email': email})
        
        user = authenticate(request, email=email, password=palavra_passe)
        if user is None:
            # Tenta autenticar pelo username caso o email não seja o username principal
            user = authenticate(request, username=email, password=palavra_passe)
            
        if user is None:
            return render(request, 'rtt/login.html', {'erro': 'Email ou palavra-passe incorretos.', 'email': email})
        
        login(request, user)
        
        # Respeita o parâmetro 'next' se existir
        next_url = request.GET.get('next') or request.POST.get('next')
        if next_url and next_url.startswith('/') and not next_url.startswith('//'):
            return redirect(next_url)
            
        # Redirecionamento baseado no tipo de utilizador
        if user.is_staff:
            return redirect('backoffice_dashboard')
        return redirect('area_utilizador')

    # Trata mensagens de erro via GET (vindo do backoffice_required, por exemplo)
    erro_get = request.GET.get('erro')
    mensagem_erro = None
    if erro_get == 'acesso_restrito':
        mensagem_erro = 'Acesso restrito a administradores.'

    return render(request, 'rtt/login.html', {'erro': mensagem_erro})


@ensure_csrf_cookie
def area_utilizador_view(request):
    """Área do utilizador após login. ?sair=1 termina sessão e redireciona para /."""
    if not request.user.is_authenticated:
        return redirect('/')
    if request.GET.get('sair') == '1':
        auth_logout(request)
        return redirect('/')
        
    try:
        profile = request.user.profile
        nome = profile.nome or request.user.email
        endereco = profile.endereco or ''
        data_nascimento = profile.data_nascimento
        departamento_nome = profile.departamento.nome if profile.departamento else ''
        jornada_nome = profile.jornada.nome if profile.jornada else ''
    except Profile.DoesNotExist:
        profile = None
        nome = request.user.email or getattr(request.user, 'username', '')
        endereco = ''
        data_nascimento = None
        departamento_nome = ''
        jornada_nome = ''

    # Lógica do Espelho de Ponto para o utilizador
    from .backoffice_views import construir_espelho
    from django.utils import timezone
    
    # Encontra a data da primeira marcação para mostrar "todo o percurso"
    primeira = Marcacao.objects.filter(utilizador=request.user).order_by('timestamp').first()
    hoje = timezone.localdate()
    
    if primeira:
        data_inicio = timezone.localtime(primeira.timestamp).date()
    else:
        data_inicio = hoje
        
    # Se houver filtro de data via GET, respeita-o (opcional, mas bom ter)
    data_fim = hoje
    
    # Gerar as linhas do espelho (reutilizando a lógica do backoffice)
    # Passamos uma lista com apenas o utilizador logado
    espelho_linhas = construir_espelho(data_inicio, data_fim, [request.user])

    email = getattr(request.user, 'email', '') or ''
    return render(request, 'rtt/area_utilizador.html', {
        'nome': nome,
        'email': email,
        'endereco': endereco,
        'data_nascimento': data_nascimento,
        'departamento_nome': departamento_nome,
        'jornada_nome': jornada_nome,
        'espelho_linhas': espelho_linhas,
        'data_inicio': data_inicio,
        'data_fim': data_fim,
    })


@require_GET
@never_cache
def viaturas_api_view(request):
    """Retorna a lista de viaturas ativas."""
    if not request.user.is_authenticated:
        return JsonResponse({'sucesso': False}, 401)
    # Filtra apenas viaturas atribuídas ao utilizador logado
    # (Pode ser via Viatura.colaborador_atual ou via Profile.viatura)
    from django.db.models import Q
    viaturas = Viatura.objects.filter(
        Q(colaborador_atual=request.user) | Q(colaboradores__user=request.user),
        ativo=True
    ).distinct().order_by('matricula')
    lista = []
    for v in viaturas:
        lista.append({
            'id': v.id,
            'matricula': v.matricula,
            'marca_modelo': v.marca_modelo,
            'km_atual': v.km_atual
        })
    return JsonResponse({'sucesso': True, 'viaturas': lista})


@csrf_exempt
@require_POST
def km_registo_view(request):
    """Registo de KM associado a uma viatura cadastrada."""
    if not request.user.is_authenticated:
        return JsonResponse({'sucesso': False, 'erro': 'Não autenticado.'}, 401)
        
    try:
        data = json.loads(request.body)
        km_valor = data.get('km')
        viatura_id = data.get('viatura_id')
        
        if km_valor is None or not viatura_id:
            return JsonResponse({'sucesso': False, 'erro': 'KM e Viatura são obrigatórios.'}, 400)
            
        viatura = get_object_or_404(Viatura, pk=viatura_id)
        
        # Validação: KM deve ser superior ao KM atual da viatura
        if km_valor < viatura.km_atual:
            return JsonResponse({
                'sucesso': False, 
                'erro': f'KM inválido. O KM atual da viatura ({viatura.matricula}) é {viatura.km_atual}.'
            }, 400)
            
        # Criar registo guardando o KM anterior da viatura
        RegistroKM.objects.create(
            utilizador=request.user,
            km=km_valor,
            km_anterior=viatura.km_atual,
            viatura=viatura,
        )
        
        # Atualizar KM atual da viatura
        viatura.km_atual = km_valor
        viatura.save()
        
        return JsonResponse({'sucesso': True, 'mensagem': 'KM registado com sucesso.'})
    except Exception as e:
        return JsonResponse({'sucesso': False, 'erro': str(e)}, 500)


@require_GET
@never_cache
def km_status_view(request):
    """Retorna a lista de registos de KM de hoje e totais (dia, semana, mês)."""
    try:
        if not request.user.is_authenticated:
            return JsonResponse({'sucesso': False}, 401)
            
        hoje = timezone.localdate()
        
        # Registos de hoje
        registos_hoje = RegistroKM.objects.filter(utilizador=request.user, data=hoje).order_by('timestamp')
        
        lista_hoje = []
        for r in registos_hoje:
            lista_hoje.append({
                'timestamp': timezone.localtime(r.timestamp).strftime('%H:%M'),
                'km': r.km,
                'viatura': r.viatura.matricula if r.viatura else '---',
                'percorrido': r.distancia
            })

        # Função auxiliar para calcular total de um período (Soma do deslocamento diário por viatura)
        def calc_total(queryset):
            from django.db.models import Max, Min
            # Agrupar por data e viatura para calcular o deslocamento do dia
            resumo = queryset.order_by().values('data', 'viatura').annotate(
                max_km=Max('km'),
                min_prev=Min('km_anterior')
            )
            soma = 0
            for r in resumo:
                if r['max_km'] is not None and r['min_prev'] is not None:
                    diff = r['max_km'] - r['min_prev']
                    if diff > 0:
                        soma += diff
            return float(soma)

        # Busca a data do primeiríssimo registo do utilizador para ser a base das médias
        primeiro_registo = RegistroKM.objects.filter(utilizador=request.user).order_by('data').first()
        data_inicio_real = primeiro_registo.data if primeiro_registo else hoje

        # Função auxiliar para calcular dias úteis/corridos para a média
        def calc_dias_periodo(inicio_periodo, data_base_sistema, data_hoje):
            # A data de início para a média deve ser a maior entre o início do período (ex: dia 1) e o primeiro registo
            inicio_efetivo = max(inicio_periodo, data_base_sistema)
            return (data_hoje - inicio_efetivo).days + 1

        # Totais
        total_hoje = calc_total(registos_hoje)
        
        # Semana (segunda a hoje)
        inicio_semana = hoje - timezone.timedelta(days=hoje.weekday())
        registos_semana = RegistroKM.objects.filter(utilizador=request.user, data__gte=inicio_semana)
        total_semana = calc_total(registos_semana)
        dias_semana = calc_dias_periodo(inicio_semana, data_inicio_real, hoje)
        media_semana = total_semana / dias_semana if dias_semana > 0 else 0
        
        # Mês (dia 1 a hoje)
        inicio_mes = hoje.replace(day=1)
        registos_mes = RegistroKM.objects.filter(utilizador=request.user, data__gte=inicio_mes)
        total_mes = calc_total(registos_mes)
        dias_mes = calc_dias_periodo(inicio_mes, data_inicio_real, hoje)
        media_mes = total_mes / dias_mes if dias_mes > 0 else 0

        # Ano (jan 1 a hoje)
        inicio_ano = hoje.replace(month=1, day=1)
        registos_ano = RegistroKM.objects.filter(utilizador=request.user, data__gte=inicio_ano)
        total_ano = calc_total(registos_ano)
        dias_ano = calc_dias_periodo(inicio_ano, data_inicio_real, hoje)
        media_ano = total_ano / dias_ano if dias_ano > 0 else 0
        
        return JsonResponse({
            'sucesso': True,
            'registos': lista_hoje,
            'totais': {
                'hoje': total_hoje,
                'semana': total_semana,
                'mes': total_mes,
                'ano': total_ano
            },
            'medias': {
                'semana': round(media_semana, 1),
                'mes': round(media_mes, 1),
                'ano': round(media_ano, 1)
            }
        })
    except Exception as e:
        return JsonResponse({'sucesso': False, 'erro': str(e)}, 500)


@require_GET
@never_cache
def service_worker_view(request):
    """Service Worker do RTT-IT (cache básico para PWA)."""
    js = r"""
const CACHE_NAME = 'rtt-it-v1';
const CORE_ASSETS = [
  '/',
  '/manifest.webmanifest',
  '/service-worker.js',
  '/static/pwa/icon.svg'
];

self.addEventListener('install', (event) => {
  event.waitUntil((async () => {
    const cache = await caches.open(CACHE_NAME);
    await cache.addAll(CORE_ASSETS);
    await self.skipWaiting();
  })());
});

self.addEventListener('activate', (event) => {
  event.waitUntil((async () => {
    const keys = await caches.keys();
    await Promise.all(keys.map((k) => (k !== CACHE_NAME ? caches.delete(k) : Promise.resolve())));
    await self.clients.claim();
  })());
});

function isNavigationRequest(request) {
  return request.mode === 'navigate' || (request.headers.get('accept') || '').includes('text/html');
}

self.addEventListener('fetch', (event) => {
  const request = event.request;
  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;

  // Não interferir com chamadas API ou Backoffice (mantém sempre rede)
  if (url.pathname.startsWith('/api/') || url.pathname.startsWith('/backoffice/') || url.pathname.startsWith('/admin/')) return;

  // Navegação: network-first com fallback para cache (login)
  if (isNavigationRequest(request)) {
    event.respondWith((async () => {
      try {
        const fresh = await fetch(request);
        if (request.method === 'GET') {
          const cache = await caches.open(CACHE_NAME);
          cache.put(request, fresh.clone());
        }
        return fresh;
      } catch (e) {
        const cached = await caches.match(request);
        return cached || caches.match('/') || new Response('Offline', { status: 200, headers: { 'Content-Type': 'text/plain; charset=utf-8' }});
      }
    })());
    return;
  }

  // Assets: cache-first (apenas para GET)
  event.respondWith((async () => {
    const cached = await caches.match(request);
    if (cached) return cached;
    
    const fresh = await fetch(request);
    if (request.method === 'GET') {
      const cache = await caches.open(CACHE_NAME);
      cache.put(request, fresh.clone());
    }
    return fresh;
  })());
});
""".strip()
    return HttpResponse(js, content_type='application/javascript; charset=utf-8')


@require_GET
@never_cache
def manifest_view(request):
    data = {
        "name": "RTT-IT - Nordigal",
        "short_name": "RTT-IT",
        "start_url": "/",
        "scope": "/",
        "display": "standalone",
        "background_color": "#F1F5F9",
        "theme_color": "#2563EB",
        "icons": [
            {
                "src": "/static/pwa/icon.svg",
                "sizes": "512x512",
                "type": "image/svg+xml",
                "purpose": "any maskable"
            }
        ]
    }
    import json
    return HttpResponse(json.dumps(data, ensure_ascii=False), content_type='application/manifest+json; charset=utf-8')

TIPO_MARCACAO_VALIDOS = {'entrada', 'inicio_almoco', 'fim_almoco', 'fim_jornada'}


def _json(data, status=200):
    return JsonResponse(data, status=status, safe=False)


def _require_auth(request):
    """Retorna (None, response) se não autenticado, ou (user, None) se autenticado."""
    if not request.user.is_authenticated:
        return None, _json({'erro': 'Autenticação necessária.'}, 401)
    return request.user, None


# ---------- Login ----------
@require_http_methods(["POST"])
@csrf_exempt
def login_view(request):
    """POST /api/login/ - email, palavra_passe. Retorna sucesso/falha e sessão (cookie)."""
    if request.method != 'POST':
        return _json({'erro': 'Método não permitido.'}, 405)
    try:
        import json
        body = json.loads(request.body.decode('utf-8')) if request.body else {}
    except Exception:
        body = getattr(request, 'POST', {}) or {}
    email = (body.get('email') or '').strip()
    palavra_passe = body.get('palavra_passe') or ''
    if not email or not palavra_passe:
        return _json({'sucesso': False, 'mensagem': 'Credenciais inválidas.'}, 400)
    user = authenticate(request, email=email, password=palavra_passe)
    if user is None:
        return _json({'sucesso': False, 'mensagem': 'Email ou palavra-passe incorretos.'}, 401)
    login(request, user)
    return _json({
        'sucesso': True,
        'mensagem': 'Autenticação realizada com sucesso.',
        'utilizador_id': user.pk,
    })


@require_GET
@never_cache
def hora_servidor(request):
    """
    GET /api/hora-servidor/ — instante atual do servidor (UTC ms) e fuso usado nos registos.
    O cliente aplica offset face ao relógio local para mostrar a mesma hora que nas marcações.
    """
    user, err = _require_auth(request)
    if err:
        return err
    now = timezone.now()
    return _json({
        'unix_ms': int(now.timestamp() * 1000),
        'time_zone': settings.TIME_ZONE,
    })


# ---------- Marcações ----------
def _marcacoes_hoje(user):
    """Marcações do utilizador hoje (data local)."""
    hoje = timezone.localdate()
    return Marcacao.objects.filter(utilizador=user, timestamp__date=hoje)


@require_http_methods(["POST"])
@csrf_exempt
def marcacao_list_create(request):
    """POST /api/marcacoes/ - criar marcação (latitude, longitude, tipo_marcacao [, justificativa]). Permite até 8 marcações/dia."""
    user, err = _require_auth(request)
    if err:
        return err
    try:
        import json
        body = json.loads(request.body.decode('utf-8')) if request.body else {}
    except Exception:
        body = getattr(request, 'POST', {}) or {}
    tipo_marcacao = (body.get('tipo_marcacao') or '').strip().lower()
    if tipo_marcacao not in TIPO_MARCACAO_VALIDOS:
        return _json({
            'sucesso': False,
            'mensagem': 'Erro ao marcar presença. Tente novamente.',
            'erro': 'tipo_marcacao inválido. Valores: entrada, inicio_almoco, fim_almoco, fim_jornada'
        }, 400)
    try:
        lat = Decimal(str(body.get('latitude')))
        lon = Decimal(str(body.get('longitude')))
    except (TypeError, InvalidOperation):
        return _json({
            'sucesso': False,
            'mensagem': 'Erro ao marcar presença. Tente novamente.',
            'erro': 'latitude e longitude são obrigatórios e numéricos.'
        }, 400)

    hoje = _marcacoes_hoje(user)
    if hoje.count() >= 4:
        return _json({
            'sucesso': False,
            'mensagem': 'Limite de 4 marcações por dia atingido.',
            'erro': 'limite_marcacoes'
        }, 400)
    # Nota: o fluxo do UI pode ciclar tipos; aqui só garantimos limite de 4 marcações/dia.
    # Se vier justificativa, guardamos; caso contrário, mantém vazio.
    justificativa = (body.get('justificativa') or '').strip()

    try:
        m = Marcacao.objects.create(
            utilizador=user,
            tipo=tipo_marcacao,
            latitude=lat,
            longitude=lon,
            justificativa=justificativa or '',
        )
        ts = timezone.localtime(m.timestamp)
        data_hora = ts.strftime('%d/%m/%Y %H:%M')
        return _json({'sucesso': True, 'mensagem': 'Presença marcada com sucesso!', 'data_hora': data_hora})
    except Exception:
        return _json({'sucesso': False, 'mensagem': 'Erro ao marcar presença. Tente novamente.'}, 500)


@require_http_methods(["GET"])
@never_cache
def minhas_marcacoes(request):
    """GET /api/marcacoes/minhas/ - lista marcações do utilizador logado, mais recentes primeiro."""
    user, err = _require_auth(request)
    if err:
        return err
    lista = []
    for m in Marcacao.objects.filter(utilizador=user).order_by('-timestamp'):
        lista.append({
            'id': str(m.id),
            'Data e Hora': timezone.localtime(m.timestamp).strftime('%Y-%m-%d %H:%M:%S'),
            'Tipo de Marcação': m.get_tipo_display(),
            'status': 'registado',
        })
    return _json(lista)


# ---------- Utilizadores (criação) ----------
@require_http_methods(["POST"])
@csrf_exempt
def utilizador_create(request):
    """POST /api/utilizadores/ - nome, email, palavra_passe. Cria utilizador (para integrações)."""
    try:
        import json
        body = json.loads(request.body.decode('utf-8')) if request.body else {}
    except Exception:
        body = getattr(request, 'POST', {}) or {}
    nome = (body.get('nome') or '').strip()
    email = (body.get('email') or '').strip().lower()
    palavra_passe = body.get('palavra_passe') or ''
    if not email:
        return _json({'sucesso': False, 'mensagem': 'Erro ao criar utilizador.', 'erro': 'Email é obrigatório.'}, 400)
    if not palavra_passe:
        return _json({'sucesso': False, 'mensagem': 'Erro ao criar utilizador.', 'erro': 'Palavra-passe é obrigatória.'}, 400)
    if User.objects.filter(email__iexact=email).exists():
        return _json({'sucesso': False, 'mensagem': 'Email já registado.'}, 409)
    try:
        user = User.objects.create_user(
            username=email,
            email=email,
            password=palavra_passe,
        )
        Profile.objects.get_or_create(user=user, defaults={'nome': nome or email})
    except Exception as e:
        return _json({'sucesso': False, 'mensagem': 'Erro ao criar utilizador.'}, 500)
    return _json({'sucesso': True, 'mensagem': 'Utilizador criado com sucesso!', 'utilizador_id': user.pk})


# ---------- Relatórios ----------
def _filtros_marcacoes(request):
    """Aplica filtros utilizador_id, data_inicio, data_fim e retorna queryset (admin/relatórios)."""
    qs = Marcacao.objects.all().select_related('utilizador').order_by('-timestamp')
    uid = request.GET.get('utilizador_id')
    if uid:
        qs = qs.filter(utilizador_id=uid)
    data_inicio = request.GET.get('data_inicio')
    data_fim = request.GET.get('data_fim')
    if data_inicio:
        try:
            from datetime import datetime
            dt = datetime.strptime(data_inicio, '%Y-%m-%d')
            qs = qs.filter(timestamp__date__gte=dt.date())
        except ValueError:
            pass
    if data_fim:
        try:
            from datetime import datetime
            dt = datetime.strptime(data_fim, '%Y-%m-%d')
            qs = qs.filter(timestamp__date__lte=dt.date())
        except ValueError:
            pass
    return qs


@require_http_methods(["GET"])
def relatorios_marcacoes(request):
    """GET /api/relatorios/marcacoes/?utilizador_id=&data_inicio=&data_fim= - linha do tempo."""
    user, err = _require_auth(request)
    if err:
        return err
    qs = _filtros_marcacoes(request)
    if not user.is_staff:
        qs = qs.filter(utilizador=user)
    lista = []
    for m in qs:
        lista.append({
            'tipo': m.get_tipo_display(),
            'hora': timezone.localtime(m.timestamp).strftime('%Y-%m-%d %H:%M:%S'),
            'utilizador_id': m.utilizador_id,
        })
    return _json(lista)


@require_GET
def relatorios_exportar_csv(request):
    """GET /api/relatorios/exportar_csv/?utilizador_id=&data_inicio=&data_fim= - exportar CSV."""
    user, err = _require_auth(request)
    if err:
        return err
    qs = _filtros_marcacoes(request)
    if not user.is_staff:
        qs = qs.filter(utilizador=user)
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="relatorio_marcacoes.csv"'
    response.write('\ufeff')  # BOM UTF-8 para Excel
    writer = csv.writer(response, delimiter=';')
    writer.writerow(['Utilizador', 'Tipo de Marcação', 'Data/Hora', 'Latitude', 'Longitude'])
    for m in qs:
        nome = getattr(m.utilizador.profile, 'nome', None) or m.utilizador.email or str(m.utilizador.pk)
        writer.writerow([
            nome,
            m.get_tipo_display(),
            timezone.localtime(m.timestamp).strftime('%Y-%m-%d %H:%M:%S'),
            str(m.latitude),
            str(m.longitude),
        ])
    return response


@require_GET
@never_cache
def km_registos_todos_view(request):
    """Retorna todos os registos de KM do utilizador logado."""
    user, err = _require_auth(request)
    if err:
        return err
    registos = RegistroKM.objects.filter(utilizador=user).order_by('-timestamp')
    lista = []
    for r in registos:
        lista.append({
            'id': r.id,
            'data': timezone.localtime(r.timestamp).strftime('%Y-%m-%d'),
            'timestamp': timezone.localtime(r.timestamp).strftime('%H:%M'),
            'km': r.km,
            'viatura': r.viatura.matricula if r.viatura else '---',
            'percorrido': r.distancia
        })
    return _json(lista)


@require_GET
@never_cache
def km_historico_view(request):
    """Retorna o histórico completo de KM agrupado por dia."""
    user, err = _require_auth(request)
    if err:
        return err
    
    from django.db.models import Max, Min
    from django.db.models.functions import TruncDate
    
    # Busca todos os registos do utilizador
    registos = RegistroKM.objects.filter(utilizador=user).annotate(
        dia=TruncDate('timestamp')
    ).values('dia', 'viatura', 'viatura__matricula').annotate(
        max_km=Max('km'),
        min_prev=Min('km_anterior')
    ).order_by('-dia')
    
    # Agrupar por dia (um dia pode ter várias viaturas)
    historico_dict = {}
    for r in registos:
        dia_str = r['dia'].strftime('%Y-%m-%d')
        dist = (r['max_km'] or 0) - (r['min_prev'] or 0)
        if dist < 0: dist = 0
        
        if dia_str not in historico_dict:
            historico_dict[dia_str] = {
                'data': r['dia'].strftime('%d/%m/%Y'),
                'total_km': 0,
                'detalhes': []
            }
        
        historico_dict[dia_str]['total_km'] += dist
        historico_dict[dia_str]['detalhes'].append({
            'viatura': r['viatura__matricula'],
            'distancia': dist
        })
    
    # Converter para lista ordenada
    resultado = sorted(historico_dict.values(), key=lambda x: x['data'], reverse=True)
    
    return _json(resultado)


from .utils_ocr import processar_recibo_ocr
from .models import Abastecimento, Cartao

@csrf_exempt
@require_POST
def abastecimento_registar_view(request):
    """POST /api/abastecimento/registar/ - Registar um abastecimento de combustível."""
    user, err = _require_auth(request)
    if err:
        return err

    try:
        viatura_id = request.POST.get('viatura_id')
        km = request.POST.get('km')
        valor = request.POST.get('valor')
        litros = request.POST.get('litros')
        metodo_pagamento = request.POST.get('metodo_pagamento', 'dinheiro')
        cartao = request.POST.get('cartao')
        comprovativo = request.FILES.get('comprovativo')

        if not viatura_id or not km or not valor or not litros:
            return _json({'sucesso': False, 'erro': 'Campos obrigatórios em falta: Viatura, KM, Valor e Litros são todos obrigatórios.'})

        # Validar método de pagamento e cartão
        cartao_obj = None
        if metodo_pagamento == 'cartao':
            if not cartao:
                return _json({'sucesso': False, 'erro': 'Por favor, indique os 4 últimos dígitos do cartão utilizado.'})
            cartao_clean = str(cartao).strip()
            if len(cartao_clean) != 4 or not cartao_clean.isdigit():
                return _json({'sucesso': False, 'erro': 'O número de cartão deve ter exatamente os 4 últimos dígitos.'})
            
            # Verificar se utilizador tem cartão ativo associado
            cartao_obj = Cartao.objects.filter(colaborador_atual=user, ativo=True).first()
            if not cartao_obj:
                return _json({'sucesso': False, 'erro': 'Não tem nenhum cartão de combustível ativo associado à sua conta. Por favor, contacte o administrador.'})
            
            # Validar os 4 últimos dígitos
            db_numero = str(cartao_obj.numero).strip()
            if len(db_numero) < 4 or db_numero[-4:] != cartao_clean:
                return _json({'sucesso': False, 'erro': 'Os 4 últimos dígitos introduzidos não correspondem ao seu cartão associado.'})
            
            cartao_final_str = f"{cartao_obj.nome} (...{cartao_clean})"
        else:
            cartao_final_str = "Dinheiro (€)"

        # Obter viatura
        try:
            viatura = Viatura.objects.get(id=viatura_id)
        except Viatura.DoesNotExist:
            return _json({'sucesso': False, 'erro': 'Viatura não encontrada.'})

        # Validar quilometragem
        km_val = int(km)
        if km_val < viatura.km_atual:
            return _json({'sucesso': False, 'erro': f'KM não pode ser menor que o atual ({viatura.km_atual}).'})

        # Validar valor
        valor_val = Decimal(str(valor).replace(',', '.'))
        if valor_val <= 0:
            return _json({'sucesso': False, 'erro': 'O valor deve ser superior a zero.'})

        # Validar litros
        try:
            litros_val = Decimal(str(litros).replace(',', '.'))
            if litros_val <= 0:
                return _json({'sucesso': False, 'erro': 'A quantidade de litros deve ser superior a zero.'})
        except (TypeError, ValueError, InvalidOperation):
            return _json({'sucesso': False, 'erro': 'Quantidade de litros inválida.'})

        # Criação do abastecimento
        abast = Abastecimento(
            utilizador=user,
            viatura=viatura,
            km=km_val,
            valor=valor_val,
            litros=litros_val,
            metodo_pagamento=metodo_pagamento,
            cartao=cartao_final_str,
            cartao_ref=cartao_obj,
            comprovativo=comprovativo,
            status='pendente'
        )

        # Se houver comprovativo, corre OCR
        if comprovativo:
            comprovativo.seek(0)
            ocr_res = processar_recibo_ocr(comprovativo)
            abast.comprovativo_texto_ocr = ocr_res.get('texto_ocr', '')
            
        abast.save()

        # Atualiza a quilometragem da viatura também se o KM do abastecimento for maior
        if km_val > viatura.km_atual:
            viatura.km_atual = km_val
            viatura.save()

        return _json({'sucesso': True, 'mensagem': 'Pedido de abastecimento registado e enviado para aprovação!'})

    except Exception as e:
        return _json({'sucesso': False, 'erro': str(e)})


@require_GET
@never_cache
def abastecimento_minhas_view(request):
    """GET /api/abastecimento/minhas/ - Listar todos os abastecimentos do utilizador logado."""
    user, err = _require_auth(request)
    if err:
        return err

    abastecimentos = Abastecimento.objects.filter(utilizador=user).order_by('-timestamp')
    lista = []
    for a in abastecimentos:
        lista.append({
            'id': a.id,
            'data': timezone.localtime(a.timestamp).strftime('%d/%m/%Y'),
            'data_iso': timezone.localtime(a.timestamp).strftime('%Y-%m-%d'),
            'hora': timezone.localtime(a.timestamp).strftime('%H:%M'),
            'km': a.km,
            'valor': float(a.valor),
            'litros': float(a.litros) if a.litros else None,
            'metodo_pagamento': a.metodo_pagamento or 'dinheiro',
            'cartao': a.cartao or '---',
            'comprovativo_url': a.comprovativo.url if a.comprovativo else None,
            'status': a.status,
            'status_label': a.get_status_display(),
            'justificativa_admin': a.justificativa_admin or '',
            'viatura': a.viatura.matricula if a.viatura else '---'
        })
    return _json(lista)


@csrf_exempt
@require_POST
def abastecimento_ocr_view(request):
    """POST /api/abastecimento/ocr/ - Analisar comprovativo em background via OCR."""
    user, err = _require_auth(request)
    if err:
        return err

    comprovativo = request.FILES.get('comprovativo')
    if not comprovativo:
        return _json({'sucesso': False, 'erro': 'Nenhum ficheiro enviado.'})

    try:
        ocr_res = processar_recibo_ocr(comprovativo)
        return _json({
            'sucesso': True,
            'valor': ocr_res.get('valor'),
            'litros': ocr_res.get('litros'),
            'texto_ocr': ocr_res.get('texto_ocr', '')
        })
    except Exception as e:
        return _json({'sucesso': False, 'erro': str(e)})
