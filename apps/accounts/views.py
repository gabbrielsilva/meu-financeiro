from django.contrib.auth import authenticate, get_user_model, login, logout
import logging
from django.db import IntegrityError, transaction
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.cache import never_cache
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from .throttling import AuthRateThrottle
from rest_framework.views import APIView

from .serializers import LoginSerializer, RegisterSerializer, UserSerializer
from .services import register_user


def csrf_failure(request, reason=""):
    return JsonResponse({"detail": "Verificação CSRF falhou."}, status=403)


@method_decorator(never_cache, name="dispatch")
@method_decorator(csrf_protect, name="dispatch")
class AuthView(APIView):
    """Enforce CSRF even for anonymous login and registration requests."""


class CsrfView(AuthView):
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({"csrfToken": get_token(request)})


class RegisterView(AuthView):
    permission_classes = [AllowAny]
    throttle_classes = [AuthRateThrottle]
    throttle_scope = "register"

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            with transaction.atomic():
                user = register_user(**serializer.validated_data)
        except IntegrityError:
            logging.getLogger(__name__).warning("Conflito no cadastro", exc_info=True)
            return Response({"email": ["Não foi possível cadastrar este e-mail."]}, status=400)
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)


class LoginView(AuthView):
    permission_classes = [AllowAny]
    throttle_classes = [AuthRateThrottle]
    throttle_scope = "login"

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = authenticate(
            request,
            username=get_user_model().objects.normalize_email(serializer.validated_data["email"]),
            password=serializer.validated_data["password"],
        )
        if user is None:
            return Response({"detail": "E-mail ou senha inválidos."}, status=400)
        login(request, user)
        return Response(UserSerializer(user).data)


class LogoutView(AuthView):
    def post(self, request):
        logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(AuthView):
    def get(self, request):
        return Response(UserSerializer(request.user).data)
