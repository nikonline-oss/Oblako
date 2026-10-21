from django.urls import path
from .views import (
    ProxyListView, ProxyCreateView,
    ProxyUpdateView, ProxyDeleteView,
    ProxyDetailView
)

app_name = 'proxies'
urlpatterns = [
    path('', ProxyListView.as_view(), name='list'),
    path('create/', ProxyCreateView.as_view(), name='create'),
    path('edit/<int:pk>/', ProxyUpdateView.as_view(), name='edit'),
    path('delete/<int:pk>/', ProxyDeleteView.as_view(), name='delete'),
    path('view/<int:pk>/', ProxyDetailView.as_view(), name='view'),
]