from django.core.cache import cache
from rest_framework import permissions, status
from rest_framework.authtoken.models import Token
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .auth_serializers import (
    PasswordLoginSerializer, PasswordResetConfirmSerializer, PasswordResetRequestSerializer,
    RequestCodeSerializer, RequestEmailCodeSerializer, VerifyCodeSerializer, VerifyEmailCodeSerializer,
)
from .serializers import BuyerProfileSerializer
from .auth_services import (
    OtpError, request_email_code, request_otp, verify_email_code, verify_otp,
    login_with_password, request_password_reset, reset_password,
)
from .auth_throttles import LoginThrottle, OtpRequestThrottle, OtpVerifyThrottle, PasswordResetThrottle


def get_jwt_tokens_for_user(user):
    try:
        refresh = RefreshToken.for_user(user)
        return {
            "refresh": str(refresh),
            "access": str(refresh.access_token),
        }
    except Exception:
        return {}


class RequestCodeView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [OtpRequestThrottle]
    authentication_classes = []

    def post(self, request):
        serializer = RequestCodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ip = request.META.get("REMOTE_ADDR", "unknown")
        ip_key = f"otp-ip:{ip}"
        ip_attempts = cache.get(ip_key, 0)
        if ip_attempts >= 20:
            return Response(
                {"detail": "Trop de demandes depuis cette adresse. Réessayez plus tard."},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )
        cache.set(ip_key, ip_attempts + 1, timeout=3600)
        try:
            result = request_otp(serializer.validated_data["phone"])
        except OtpError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            {"detail": "Si le numéro est éligible, un code a été envoyé.", **result},
            status=status.HTTP_200_OK,
        )


class VerifyCodeView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [OtpVerifyThrottle]
    authentication_classes = []

    def post(self, request):
        serializer = VerifyCodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            result = verify_otp(
                serializer.validated_data["phone"],
                serializer.validated_data["code"],
                serializer.validated_data.get("password", ""),
            )
        except OtpError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        token, _ = Token.objects.get_or_create(user=result["user"])
        jwt_tokens = get_jwt_tokens_for_user(result["user"])
        account = result["account"]
        buyer_profile = getattr(result["user"], "buyer_profile", None)
        profile_configured = bool(
            buyer_profile
            and buyer_profile.region_id
            and buyer_profile.locality_id
        )
        return Response(
            {
                "token": token.key,
                **jwt_tokens,
                "user": {
                    "id": result["user"].id,
                    "username": result["user"].username,
                },
                "account": {
                    "phone": account.phone_e164,
                    "role": account.role,
                    "phone_verified": account.phone_verified,
                    "email": account.email,
                    "email_verified": account.email_verified,
                },
                "buyer_profile": BuyerProfileSerializer(buyer_profile).data if buyer_profile else None,
                "profile_configured": profile_configured,
            },
            status=status.HTTP_200_OK,
        )


class MeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        account = getattr(request.user, "phone_account", None)
        profile = getattr(request.user, "buyer_profile", None)
        profile_data = BuyerProfileSerializer(profile).data if profile else None
        return Response(
            {
                "user": {"id": request.user.id, "username": request.user.username},
                "profile": profile_data,
                "buyer_profile": profile_data,
                "profile_configured": bool(profile and profile.region_id and profile.locality_id),
                "account": {
                    "phone": account.phone_e164 if account else None,
                    "role": account.role if account else None,
                    "phone_verified": account.phone_verified if account else False,
                    "email": account.email if account else None,
                    "email_verified": account.email_verified if account else False,
                },
            }
        )


class RequestEmailCodeView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [OtpRequestThrottle]
    authentication_classes = []

    def post(self, request):
        serializer = RequestEmailCodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            result = request_email_code(serializer.validated_data["email"])
        except OtpError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"detail": "Un code a été envoyé à cette adresse si elle est valide.", **result}, status=status.HTTP_200_OK)


class VerifyEmailCodeView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [OtpVerifyThrottle]
    authentication_classes = []

    def post(self, request):
        serializer = VerifyEmailCodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            result = verify_email_code(
                serializer.validated_data["email"],
                serializer.validated_data["code"],
                serializer.validated_data.get("password", ""),
            )
        except OtpError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        token, _ = Token.objects.get_or_create(user=result["user"])
        jwt_tokens = get_jwt_tokens_for_user(result["user"])
        account = result["account"]
        buyer_profile = getattr(result["user"], "buyer_profile", None)
        return Response(
            {
                "token": token.key,
                **jwt_tokens,
                "user": {"id": result["user"].id, "username": result["user"].username},
                "account": {
                    "phone": account.phone_e164,
                    "email": account.email,
                    "role": account.role,
                    "phone_verified": account.phone_verified,
                    "email_verified": account.email_verified,
                },
                "buyer_profile": BuyerProfileSerializer(buyer_profile).data if buyer_profile else None,
                "profile_configured": bool(buyer_profile and buyer_profile.region_id and buyer_profile.locality_id),
            },
            status=status.HTTP_200_OK,
        )


class PasswordLoginView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [LoginThrottle]
    authentication_classes = []

    def post(self, request):
        serializer = PasswordLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            result = login_with_password(serializer.validated_data["identifier"], serializer.validated_data["password"])
        except OtpError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_401_UNAUTHORIZED)
        account = result["account"]
        profile = getattr(result["user"], "buyer_profile", None)
        token, _ = Token.objects.get_or_create(user=result["user"])
        jwt_tokens = get_jwt_tokens_for_user(result["user"])
        return Response({
            "token": token.key,
            **jwt_tokens,
            "user": {"id": result["user"].id, "username": result["user"].username},
            "account": {
                "phone": account.phone_e164,
                "email": account.email,
                "role": account.role,
                "phone_verified": account.phone_verified,
                "email_verified": account.email_verified,
            },
            "buyer_profile": BuyerProfileSerializer(profile).data if profile else None,
            "profile_configured": bool(profile and profile.region_id and profile.locality_id),
        })


class PasswordResetRequestView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [PasswordResetThrottle]
    authentication_classes = []

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            result = request_password_reset(serializer.validated_data["identifier"])
        except OtpError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(result)


class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        Token.objects.filter(user=request.user).delete()
        refresh_token = request.data.get("refresh")
        if refresh_token:
            try:
                token = RefreshToken(refresh_token)
                token.blacklist()
            except Exception:
                pass
        return Response({"detail": "Session terminée."}, status=status.HTTP_200_OK)


class PasswordResetConfirmView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [PasswordResetThrottle]
    authentication_classes = []

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            reset_password(serializer.validated_data["identifier"], serializer.validated_data["code"], serializer.validated_data["password"])
        except OtpError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"detail": "Mot de passe réinitialisé. Vous pouvez vous connecter."})


class ChangePasswordView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        old_password = str(request.data.get("old_password", "")).strip()
        new_password = str(request.data.get("new_password", "")).strip()
        if not old_password or not new_password:
            return Response(
                {"detail": "L'ancien et le nouveau mot de passe sont obligatoires."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if len(new_password) < 6:
            return Response(
                {"detail": "Le nouveau mot de passe doit comporter au moins 6 caractères."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not request.user.check_password(old_password):
            return Response(
                {"detail": "L'ancien mot de passe est incorrect."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            from django.contrib.auth.password_validation import validate_password
            validate_password(new_password, user=request.user)
        except Exception as exc:
            msg = list(exc.messages) if hasattr(exc, "messages") else str(exc)
            return Response({"detail": msg}, status=status.HTTP_400_BAD_REQUEST)
        request.user.set_password(new_password)
        request.user.save(update_fields=["password"])
        return Response({"detail": "Mot de passe modifié avec succès."}, status=status.HTTP_200_OK)


