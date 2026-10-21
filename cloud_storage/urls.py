from django.urls import path

from . import views

app_name = 'cloud_storage'
urlpatterns = [
    path('', views.browse, name='browse'),
    path('account/', views.account, name='account'),
    path('info/', views.metadata, name='metadata'),
    path('download/', views.download, name='download'),
    path('folder/create/', views.create_folder, name='create_folder'),
    path('upload/', views.upload, name='upload'),
    path('move/', views.move, name='move'),
    path('copy/', views.copy, name='copy'),
    path('delete/', views.delete, name='delete'),
    path('share/', views.share, name='share'),
    path('shared/', views.shared, name='shared'),
    path('shared/revoke/', views.revoke, name='revoke'),
    path('search/', views.search, name='search'),
    path('connect/', views.connect, name='connect'),
    path('disconnect/', views.disconnect, name='disconnect'),
]
