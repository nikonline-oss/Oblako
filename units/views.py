from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import ProtectedError
from django.http import HttpResponseRedirect
from django.contrib import messages
from .models import Unit

class UnitListView(ListView):
    model = Unit
    template_name = 'units/list.html'
    context_object_name = 'units'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = "Единицы измерения"
        return context

class UnitCreateView(SuccessMessageMixin, CreateView):
    model = Unit
    fields = ['name']
    template_name = 'units/create.html'
    success_url = reverse_lazy('units:list')
    success_message = "Единица измерения добавлена"

class UnitUpdateView(SuccessMessageMixin, UpdateView):
    model = Unit
    fields = ['name']
    template_name = 'units/edit.html'
    success_url = reverse_lazy('units:list')
    success_message = "Изменения сохранены"

class UnitDeleteView(DeleteView):
    model = Unit
    success_url = reverse_lazy('units:list')
    template_name = 'units/delete.html'

    def post(self, request, *args, **kwargs):
        try:
            return self.delete(request, *args, **kwargs)
        except ProtectedError:
            messages.error(request, 'Невозможно удалить: единица измерения используется в товарах.')
            return HttpResponseRedirect(self.success_url)