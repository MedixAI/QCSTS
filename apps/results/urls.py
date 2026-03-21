from django.urls import path
from apps.results import views

urlpatterns = [
    path("", views.TestResultListCreateView.as_view(), name="result-list-create"),
    path("<uuid:pk>/", views.TestResultDetailView.as_view(), name="result-detail"),
    path("signature/verify/", views.SignatureVerifyView.as_view(), name="signature-verify"),
]
