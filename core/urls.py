from django.urls import include, path

from core.views.health import health  # adjust if you import differently

urlpatterns = [
    path("health/", health, name="health"),
    path("auth/", include("core.api.v1.auth_urls")),
    path("", include("core.api.v1.urls")),
]
