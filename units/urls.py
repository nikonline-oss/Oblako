from django.urls import path
from .views import UnitListView, UnitCreateView, UnitUpdateView, UnitDeleteView

app_name = 'units'
urlpatterns = [
    path('', UnitListView.as_view(), name='list'),
    path('create/', UnitCreateView.as_view(), name='create'),
    path('edit/<int:pk>/', UnitUpdateView.as_view(), name='edit'),
    path('delete/<int:pk>/', UnitDeleteView.as_view(), name='delete'),
]