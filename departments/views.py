from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import ProtectedError
from django.http import HttpResponseRedirect
from django.contrib import messages
from .models import Department

class DepartmentListView(ListView):
    model = Department
    template_name = 'departments/list.html'
    context_object_name = 'departments'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = "Отделы"
        return context

class DepartmentCreateView(SuccessMessageMixin, CreateView):
    model = Department
    fields = ['name']
    template_name = 'departments/create.html'
    success_url = reverse_lazy('departments:list')
    success_message = "Отдел успешно добавлен"

class DepartmentUpdateView(SuccessMessageMixin, UpdateView):
    model = Department
    fields = ['name']
    template_name = 'departments/edit.html'
    success_url = reverse_lazy('departments:list')
    success_message = "Изменения сохранены"

class DepartmentDeleteView(DeleteView):
    model = Department
    success_url = reverse_lazy('departments:list')
    template_name = 'departments/delete.html'

    def post(self, request, *args, **kwargs):
        try:
            return self.delete(request, *args, **kwargs)
        except ProtectedError:
            messages.error(request, 'Невозможно удалить: отдел используется в других документах.')
            return HttpResponseRedirect(self.success_url)