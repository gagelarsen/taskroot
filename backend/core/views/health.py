from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response


@extend_schema(
    tags=["health"],
    summary="Health check",
    description="Simple health check endpoint that returns OK status. No authentication required.",
    responses={
        200: inline_serializer(
            name="HealthResponse",
            fields={"status": serializers.CharField(default="ok")},
        )
    },
)
@api_view(["GET"])
@permission_classes([AllowAny])
def health(request):
    return Response({"status": "ok"})
