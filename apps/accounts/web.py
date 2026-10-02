from types import SimpleNamespace
import logging
from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.shortcuts import redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST, require_http_methods
from .throttling import AuthRateThrottle, AuthThrottleUnavailable
from .forms import LoginForm, RegisterForm
from .serializers import LoginSerializer, RegisterSerializer
from .services import register_user


def check_auth_throttle(request, scope, form):
    try:
        allowed = AuthRateThrottle().allow_request(request, SimpleNamespace(throttle_scope=scope))
    except AuthThrottleUnavailable:
        form.add_error(None, "Não foi possível verificar o acesso. Tente novamente em instantes.")
        return 503
    if not allowed:
        form.add_error(None, "Muitas tentativas. Aguarde antes de tentar novamente.")
    return 200 if allowed else 429


@never_cache
@require_http_methods(["GET", "POST"])
def register_page(request):
    if request.user.is_authenticated:
        return redirect("home")
    form = RegisterForm(request.POST if request.method == "POST" else None)
    response_status = 200
    if request.method == "POST":
        valid = form.is_valid()
        response_status = check_auth_throttle(request, "register", form)
        if response_status != 200:
            pass
        elif valid:
            serializer = RegisterSerializer(data={key: form.cleaned_data[key] for key in ("email", "password")})
            if serializer.is_valid():
                try:
                    register_user(**serializer.validated_data)
                except IntegrityError:
                    logging.getLogger(__name__).warning("Conflito no cadastro", exc_info=True)
                    form.add_error("email", "Não foi possível cadastrar este e-mail.")
                else:
                    messages.success(request, "Conta criada! Entre para começar.")
                    return redirect("login")
            else:
                form.add_serializer_errors(serializer.errors)
    return render(request, "accounts/auth.html", {"form": form, "register": True, "title": "Criar conta"}, status=response_status)


@never_cache
@require_http_methods(["GET", "POST"])
def login_page(request):
    if request.user.is_authenticated:
        return redirect("home")
    form = LoginForm(request.POST if request.method == "POST" else None)
    response_status = 200
    if request.method == "POST":
        valid = form.is_valid()
        response_status = check_auth_throttle(request, "login", form)
        if response_status != 200:
            pass
        elif valid:
            serializer = LoginSerializer(data=form.cleaned_data)
            if serializer.is_valid():
                user = authenticate(request, username=get_user_model().objects.normalize_email(serializer.validated_data["email"]), password=serializer.validated_data["password"])
                if user:
                    login(request, user)
                    return redirect("home")
                form.add_error(None, "E-mail ou senha inválidos.")
            else:
                form.add_serializer_errors(serializer.errors)
    return render(request, "accounts/auth.html", {"form": form, "title": "Entrar"}, status=response_status)


@never_cache
@login_required
@require_POST
def logout_page(request):
    logout(request)
    return redirect("login")


@never_cache
@login_required
def settings_page(request):
    return render(request, "accounts/settings.html", {"title": "Configurações"})
