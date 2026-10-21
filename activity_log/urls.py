from django.urls import path

from . import views

app_name = 'activity_log'
urlpatterns = [
    path('', views.journal, name='journal'),
    path('stats/', views.stats, name='stats'),
    path('series/', views.series_list, name='series'),
    path('series/new/', views.series_create, name='series_create'),
    path('series/<str:series_id>/edit/', views.series_edit, name='series_edit'),
    path('series/<str:series_id>/delete/', views.series_delete, name='series_delete'),
    path('<str:event_id>/', views.event_detail, name='detail'),
]
