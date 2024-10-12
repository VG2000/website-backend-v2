from django.urls import path
from . import views

app_name = "investment"

urlpatterns = [
     path('update-tradingview/', views.TradingViewUploadView.as_view(), name='update-tradingview'),
     path("update-instruments/", views.InstrumentUploadView.as_view(), name="update-instruments"),
     path('update-monthly/', views.MonthlyVolumesUploadView.as_view(), name="update-monthly"),
     path("update-weekly/", views.WeeklyVolumesUploadView.as_view(), name="update-weekly"),
     path('download-no-metadata/', views.UploadNoMetadataCSVView.as_view(), name='download-no-metadata'),
     path('get-temporary-credentials/', views.GetTemporaryCredentialsView.as_view(), name='get-temporary-credentials'),
     path('get-presigned-url/', views.GetPresignedUrlView.as_view(), name='get-presigned-url'),
     path("tradingview/", views.TradingviewObjectiveViewSet.as_view({'get': 'list'}), name="tradingview"),
     path("add-to-watchlist/", views.WatchlistCreateView.as_view(), name="add-to-watchlist"),
     path("delete-from-watchlist/<str:id>/", views.WatchlistDeleteView.as_view(), name="delete-from-watchlist"),
]