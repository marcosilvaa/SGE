from django.contrib import admin
from django.urls import path, include
from . import views


urlpatterns = [
    path('health/', views.health, name='health'),
    path('admin/', admin.site.urls),
    path('login/', views.demo_entry, name='login'),
    path('logout/', views.demo_entry, name='logout'),
    path('api/v1/', include('authentication.urls')),
    path('', views.landing, name='landing'),
    path('dashboard/', views.home, name='home'),
    path('', include('brands.urls')),
    path('', include('categories.urls')),
    path('', include('suppliers.urls')),
    path('', include('inflows.urls')),
    path('', include('outflows.urls')),
    path('', include('products.urls')),
]
