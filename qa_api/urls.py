"""URL configuration for qa_api project."""
from django.urls import path

from ask.views import AskAPIView, HealthAPIView

urlpatterns = [
    path("", HealthAPIView.as_view(), name="health"),
    path("api/ask/", AskAPIView.as_view(), name="ask"),
]
