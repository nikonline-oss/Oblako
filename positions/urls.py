from django.urls import path
from .views import PositionListView, PositionCreateView, PositionUpdateView, PositionDeleteView

app_name = 'positions'
urlpatterns = [
    path('', PositionListView.as_view(), name='list'),
    path('create/', PositionCreateView.as_view(), name='create'),
    path('edit/<int:pk>/', PositionUpdateView.as_view(), name='edit'),
    path('delete/<int:pk>/', PositionDeleteView.as_view(), name='delete'),
]