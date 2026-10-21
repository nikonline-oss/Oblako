from django.urls import path
from .views import CustomerListView, CustomerCreateView, CustomerUpdateView, CustomerDeleteView

app_name = 'customers'
urlpatterns = [
    path('', CustomerListView.as_view(), name='list'),
    path('create/', CustomerCreateView.as_view(), name='create'),
    path('edit/<int:pk>/', CustomerUpdateView.as_view(), name='edit'),
    path('delete/<int:pk>/', CustomerDeleteView.as_view(), name='delete'),
]