from django.urls import path
from .views import AccountListView, AccountCreateView, AccountUpdateView, AccountDeleteView

app_name = 'accounts'
urlpatterns = [
    path('', AccountListView.as_view(), name='list'),
    path('create/', AccountCreateView.as_view(), name='create'),
    path('edit/<int:pk>/', AccountUpdateView.as_view(), name='edit'),
    path('delete/<int:pk>/', AccountDeleteView.as_view(), name='delete'),
]