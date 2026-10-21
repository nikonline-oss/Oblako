from django.urls import path
from .views import DepartmentListView, DepartmentCreateView, DepartmentUpdateView, DepartmentDeleteView

app_name = 'departments'
urlpatterns = [
    path('', DepartmentListView.as_view(), name='list'),
    path('create/', DepartmentCreateView.as_view(), name='create'),
    path('edit/<int:pk>/', DepartmentUpdateView.as_view(), name='edit'),
    path('delete/<int:pk>/', DepartmentDeleteView.as_view(), name='delete'),
]