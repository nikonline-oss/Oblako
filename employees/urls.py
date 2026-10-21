from django.urls import path
from .views import EmployeeListView, EmployeeCreateView, EmployeeUpdateView, EmployeeDeleteView

app_name = 'employees'
urlpatterns = [
    path('', EmployeeListView.as_view(), name='list'),
    path('create/', EmployeeCreateView.as_view(), name='create'),
    path('edit/<int:pk>/', EmployeeUpdateView.as_view(), name='edit'),
    path('delete/<int:pk>/', EmployeeDeleteView.as_view(), name='delete'),
]