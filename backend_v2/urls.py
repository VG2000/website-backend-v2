from django.contrib import admin
from django.urls import path, include
from portal.views import CustomLoginView, LogoutView

urlpatterns = [
    path("admin/", admin.site.urls),
    path('api/login/', CustomLoginView.as_view(), name='custom_login_cbv'),
    path('api/logout/', LogoutView.as_view(), name='logout'),
    path('api/portal/', include('portal.urls')),
]

