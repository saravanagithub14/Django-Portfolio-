"""
portfolio_hub URL Configuration
"""
from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView
from django.conf import settings
from django.conf.urls.static import static

from chatbot import views as chatbot_views

urlpatterns = [
    path('admin/', admin.site.urls),
    # Short, memorable entry point to the admin (shows the login form if not signed in)
    path('login/', RedirectView.as_view(url='/admin/', permanent=False)),
    path('chatbot/', include('chatbot.urls')),
    path('health', chatbot_views.health_view, name='health'),
    path('update_context', chatbot_views.update_context_view, name='update_context'),
    path('', include('portfolio.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
