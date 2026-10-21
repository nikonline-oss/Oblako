from django.urls import path
from .views import BrigadierListView, BrigadierCreateView, BrigadierUpdateView, BrigadierDeleteView

app_name = 'brigadier'
urlpatterns = [
    path('', BrigadierListView.as_view(), name='list'),
    path('create/', BrigadierCreateView.as_view(), name='create'),
    path('edit/<int:pk>/', BrigadierUpdateView.as_view(), name='edit'),
    path('delete/<int:pk>/', BrigadierDeleteView.as_view(), name='delete'),
]