from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import ProtectedError
from django.http import HttpResponseRedirect
from django.contrib import messages
from .models import Employee

class EmployeeListView(ListView):
    model = Employee
    template_name = 'employees/list.html'
    context_object_name = 'employees'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = "Сотрудники"
        return context

class EmployeeCreateView(SuccessMessageMixin, CreateView):
    model = Employee
    fields = [
        'last_name', 'first_name', 'middle_name', 'post',
        'passport_series', 'passport_number',
        'passport_issued_by', 'passport_date_of_issue'
    ]
    template_name = 'employees/create.html'
    success_url = reverse_lazy('employees:list')
    success_message = "Сотрудник успешно добавлен"

class EmployeeUpdateView(SuccessMessageMixin, UpdateView):
    model = Employee
    fields = [
        'last_name', 'first_name', 'middle_name', 'post',
        'passport_series', 'passport_number',
        'passport_issued_by', 'passport_date_of_issue'
    ]
    template_name = 'employees/edit.html'
    success_url = reverse_lazy('employees:list')
    success_message = "Изменения сохранены"

class EmployeeDeleteView(DeleteView):
    model = Employee
    success_url = reverse_lazy('employees:list')
    template_name = 'employees/delete.html'

    def post(self, request, *args, **kwargs):
        try:
            return self.delete(request, *args, **kwargs)
        except ProtectedError:
            messages.error(request, 'Невозможно удалить: сотрудник используется в других документах.')
            return HttpResponseRedirect(self.success_url)