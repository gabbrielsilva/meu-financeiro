from types import SimpleNamespace
from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.shortcuts import redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST, require_http_methods
from rest_framework.throttling import ScopedRateThrottle
from .forms import LoginForm, RegisterForm
from .serializers import LoginSerializer, RegisterSerializer
from .services import register_user


def check_auth_throttle(request, scope, form):
    allowed = ScopedRateThrottle().allow_request(request, SimpleNamespace(throttle_scope=scope))
    if not allowed:
        form.add_error(None, "Muitas tentativas. Aguarde antes de tentar novamente.")
    return allowed


@never_cache
@require_http_methods(["GET", "POST"])
def register_page(request):
    if request.user.is_authenticated:
        return redirect("home")
    form = RegisterForm(request.POST if request.method == "POST" else None)
    response_status = 200
    if request.method == "POST":
        valid = form.is_valid()
        if not check_auth_throttle(request, "register", form):
            response_status = 429
        elif valid:
            serializer = RegisterSerializer(data={key: form.cleaned_data[key] for key in ("email", "password")})
            if serializer.is_valid():
                try:
                    register_user(**serializer.validated_data)
                except IntegrityError:
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
        if not check_auth_throttle(request, "login", form):
            response_status = 429
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
