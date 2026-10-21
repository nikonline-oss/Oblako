from django.urls import path
from .views import OrganizationListView, OrganizationCreateView, OrganizationUpdateView, OrganizationDeleteView

app_name = 'organizations'
urlpatterns = [
    path('', OrganizationListView.as_view(), name='list'),
    path('create/', OrganizationCreateView.as_view(), name='create'),
    path('edit/<int:pk>/', OrganizationUpdateView.as_view(), name='edit'),
    path('delete/<int:pk>/', OrganizationDeleteView.as_view(), name='delete'),
]