from django.urls import path  # type: ignore[import-not-found]
from .views import MEAnalyzerAPIView, DashboardStatsAPIView # <-- DashboardStatsAPIView import karein

urlpatterns = [
    path('analyze-me/', MEAnalyzerAPIView.as_view(), name='analyze_me'),
    path('dashboard-stats/', DashboardStatsAPIView.as_view(), name='dashboard_stats'), # <-- Ye line add karein
]