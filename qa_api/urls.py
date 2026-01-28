"""URL configuration for qa_api project."""
from django.contrib import admin
from django.urls import path

from ask.views import AskAPIView, HealthAPIView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", HealthAPIView.as_view(), name="health"),
    path("api/ask/", AskAPIView.as_view(), name="ask"),
]
