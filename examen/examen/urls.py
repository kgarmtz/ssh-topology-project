from django.contrib import admin
from django.urls import path, re_path, include
# Importamos los settings
from django.conf import settings
# Importamos los archivos estáticos
from django.conf.urls.static import static

"""
Debemos indicarle a Django que dentro de las urls también considere 
las urls generadas para los archivos multimedia (todo lo que se subirá
dentro del directorio 'media'):
- static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
"""

urlpatterns = [
    path('admin/', admin.site.urls),
    re_path('', include('applications.network.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)