from django.urls import path
from . import views

app_name = "investment"

urlpatterns = [
     path('update-tradingview/', views.TradingViewUploadView.as_view(), name='update-tradingview'),
     path("update-instruments/", views.InstrumentUploadView.as_view(), name="update-instruments"),
     path('update-monthly/', views.MonthlyVolumesUploadView.as_view(), name="update-monthly"),
     path("update-weekly/", views.WeeklyVolumesUploadView.as_view(), name="update-weekly"),
     path('download-no-metadata/', views.UploadNoMetadataCSVView.as_view(), name='download-no-metadata'),
]