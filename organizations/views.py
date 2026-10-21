from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import ProtectedError
from django.http import HttpResponseRedirect
from django.contrib import messages
from .models import Organization

class OrganizationListView(ListView):
    model = Organization
    template_name = 'organizations/list.html'
    context_object_name = 'organizations'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = "Организации"
        return context

class OrganizationCreateView(SuccessMessageMixin, CreateView):
    model = Organization
    fields = ['name', 'address', 'account', 'chief', 'financial_chief']
    template_name = 'organizations/create.html'
    success_url = reverse_lazy('organizations:list')
    success_message = "Организация успешно добавлена"

class OrganizationUpdateView(SuccessMessageMixin, UpdateView):
    model = Organization
    fields = ['name', 'address', 'account', 'chief', 'financial_chief']
    template_name = 'organizations/edit.html'
    success_url = reverse_lazy('organizations:list')
    success_message = "Изменения сохранены"

class OrganizationDeleteView(DeleteView):
    model = Organization
    success_url = reverse_lazy('organizations:list')
    template_name = 'organizations/delete.html'

    def post(self, request, *args, **kwargs):
        try:
            return self.delete(request, *args, **kwargs)
        except ProtectedError:
            messages.error(request, 'Невозможно удалить: организация используется в других документах.')
            return HttpResponseRedirect(self.success_url)