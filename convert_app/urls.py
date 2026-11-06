from django.urls import path
from . import views


urlpatterns = [
    path('', views.home, name='home'),
    path('transcribe/', views.transcribe, name='transcribe'),
    path('api/transcribe', views.api_transcribe, name='api_transcribe'),
    path('generate_pdf/', views.generate_pdf, name='generate_pdf'),
    path('make-pdf/', views.make_pdf, name='make_pdf'),
]