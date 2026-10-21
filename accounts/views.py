from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from .models import Account

class AccountListView(ListView):
    model = Account  # Это обязательное поле
    template_name = 'accounts/list.html'
    context_object_name = 'accounts'

class AccountCreateView(CreateView):
    model = Account
    fields = ['account', 'bank_name', 'bank_identity_number']
    template_name = 'accounts/create.html'
    success_url = reverse_lazy('accounts:list')

class AccountUpdateView(UpdateView):
    model = Account
    fields = ['account', 'bank_name', 'bank_identity_number']
    template_name = 'accounts/edit.html'
    success_url = reverse_lazy('accounts:list')

class AccountDeleteView(DeleteView):
    model = Account
    template_name = 'accounts/delete.html'
    success_url = reverse_lazy('accounts:list')