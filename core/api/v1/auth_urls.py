from django.urls import path
from drf_spectacular.utils import OpenApiExample, extend_schema
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView, TokenVerifyView


# Wrap JWT views with OpenAPI schema documentation
class DocumentedTokenObtainPairView(TokenObtainPairView):
    @extend_schema(
        tags=["auth"],
        summary="Obtain JWT token pair",
        description="Authenticate with username and password to receive access and refresh tokens.",
        examples=[
            OpenApiExample(
                "Admin login",
                value={"username": "admin", "password": "admin123"},
                request_only=True,
            ),
            OpenApiExample(
                "Token response",
                value={
                    "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                    "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                },
                response_only=True,
            ),
        ],
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class DocumentedTokenRefreshView(TokenRefreshView):
    @extend_schema(
        tags=["auth"],
        summary="Refresh JWT access token",
        description="Use a refresh token to obtain a new access token.",
        examples=[
            OpenApiExample(
                "Refresh request",
                value={"refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."},
                request_only=True,
            ),
            OpenApiExample(
                "New access token",
                value={"access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."},
                response_only=True,
            ),
        ],
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class DocumentedTokenVerifyView(TokenVerifyView):
    @extend_schema(
        tags=["auth"],
        summary="Verify JWT token",
        description="Check if a token is valid and not expired.",
        examples=[
            OpenApiExample(
                "Verify request",
                value={"token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."},
                request_only=True,
            ),
        ],
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


urlpatterns = [
    path("token/", DocumentedTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("token/refresh/", DocumentedTokenRefreshView.as_view(), name="token_refresh"),
    path("token/verify/", DocumentedTokenVerifyView.as_view(), name="token_verify"),
]
