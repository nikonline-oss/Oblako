from django.urls import path
from .views import (
    NariadListView, NariadCreateView,
    NariadUpdateView, NariadDeleteView,
    NariadDetailView
)

app_name = 'nariads'
urlpatterns = [
    path('', NariadListView.as_view(), name='list'),
    path('create/', NariadCreateView.as_view(), name='create'),
    path('edit/<int:pk>/', NariadUpdateView.as_view(), name='edit'),
    path('delete/<int:pk>/', NariadDeleteView.as_view(), name='delete'),
    path('view/<int:pk>/', NariadDetailView.as_view(), name='view'),
]