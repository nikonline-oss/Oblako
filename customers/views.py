from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import ProtectedError
from django.http import HttpResponseRedirect
from django.contrib import messages
from .models import Customer

class CustomerListView(ListView):
    model = Customer
    template_name = 'customers/list.html'
    context_object_name = 'customers'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = "Контрагенты"
        return context

class CustomerCreateView(SuccessMessageMixin, CreateView):
    model = Customer
    fields = ['name']
    template_name = 'customers/create.html'
    success_url = reverse_lazy('customers:list')
    success_message = "Контрагент успешно добавлен"

class CustomerUpdateView(SuccessMessageMixin, UpdateView):
    model = Customer
    fields = ['name']
    template_name = 'customers/edit.html'
    success_url = reverse_lazy('customers:list')
    success_message = "Изменения сохранены"

class CustomerDeleteView(DeleteView):
    model = Customer
    success_url = reverse_lazy('customers:list')
    template_name = 'customers/delete.html'

    def post(self, request, *args, **kwargs):
        try:
            return self.delete(request, *args, **kwargs)
        except ProtectedError:
            messages.error(request, 'Невозможно удалить: контрагент используется в других документах.')
            return HttpResponseRedirect(self.success_url)