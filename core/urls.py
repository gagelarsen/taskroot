from django.urls import include, path

from core.views.health import health  # adjust if you import differently

urlpatterns = [
    path("health/", health, name="health"),
    path("", include("core.api.v1.urls")),
]
