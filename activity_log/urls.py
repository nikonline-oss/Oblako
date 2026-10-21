from django.urls import path

from . import views

app_name = 'activity_log'
urlpatterns = [
    path('', views.journal, name='journal'),
    path('stats/', views.stats, name='stats'),
    path('<str:event_id>/', views.event_detail, name='detail'),
]
