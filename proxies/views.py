from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView
from django.urls import reverse_lazy
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import ProtectedError
from django.http import HttpResponseRedirect
from django.contrib import messages
from .models import Proxy
from .forms import ProxyForm, ProxyItemFormSet

from django.template.loader import render_to_string

class ProxyListView(ListView):
    model = Proxy
    template_name = 'proxies/list.html'
    context_object_name = 'proxies'

    def get_queryset(self):
        return Proxy.objects.select_related(
            'organization', 'employee', 'customer'
        ).order_by('-date_of_issue')

class ProxyCreateView(SuccessMessageMixin, CreateView):
    model = Proxy
    form_class = ProxyForm
    template_name = 'proxies/create.html'
    success_url = reverse_lazy('proxies:list')
    success_message = "Доверенность успешно создана"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['formset'] = ProxyItemFormSet(self.request.POST)
        else:
            context['formset'] = ProxyItemFormSet()
        
        # Добавляем HTML пустой формы
        empty_form = context['formset'].empty_form
        context['empty_form_html'] = render_to_string('includes/empty_row.html', {
            'form': empty_form
        })
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        formset = context['formset']
        if formset.is_valid():
            self.object = form.save()
            formset.instance = self.object
            formset.save()
            return super().form_valid(form)
        else:
            return self.render_to_response(self.get_context_data(form=form))

class ProxyUpdateView(SuccessMessageMixin, UpdateView):
    model = Proxy
    form_class = ProxyForm
    template_name = 'proxies/edit.html'
    success_url = reverse_lazy('proxies:list')
    success_message = "Изменения сохранены"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['formset'] = ProxyItemFormSet(self.request.POST, instance=self.object)
        else:
            context['formset'] = ProxyItemFormSet(instance=self.object)
        # Добавляем HTML пустой формы
        empty_form = context['formset'].empty_form
        context['empty_form_html'] = render_to_string('includes/empty_row.html', {
            'form': empty_form
        })
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        formset = context['formset']
        if formset.is_valid():
            self.object = form.save()
            formset.instance = self.object
            formset.save()
            return super().form_valid(form)
        else:
            return self.render_to_response(self.get_context_data(form=form))

class ProxyDeleteView(DeleteView):
    model = Proxy
    success_url = reverse_lazy('proxies:list')
    template_name = 'proxies/delete.html'

    def post(self, request, *args, **kwargs):
        try:
            return self.delete(request, *args, **kwargs)
        except ProtectedError:
            messages.error(request, 'Невозможно удалить: доверенность используется в других документах.')
            return HttpResponseRedirect(self.success_url)

class ProxyDetailView(DetailView):
    model = Proxy
    template_name = 'proxies/view.html'
    context_object_name = 'proxy'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['items'] = self.object.items.select_related('product', 'product__unit')
        return context