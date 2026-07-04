from django.urls import path
from chatbot import views

urlpatterns = [
    path('api/chat/', views.chat_api_endpoint, name='chat_api'),
]
