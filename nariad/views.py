from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView
from django.urls import reverse_lazy
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import ProtectedError
from django.http import HttpResponseRedirect
from django.contrib import messages
from django.template.loader import render_to_string
from .models import Nariad
from .forms import NariadForm, NariadItemFormSet, NariadItemFisFormSet

class NariadListView(ListView):
    model = Nariad
    template_name = 'nariads/list.html'
    context_object_name = 'nariads'

    def get_queryset(self):
        return Nariad.objects.select_related(
            'organization', 'brigadier', 'responsible', 
            'issued_man', 'received', 'rationer'
        ).order_by('-date_of_issue')

class NariadCreateView(SuccessMessageMixin, CreateView):
    model = Nariad
    form_class = NariadForm
    template_name = 'nariads/create.html'
    success_url = reverse_lazy('nariads:list')
    success_message = "Наряд успешно создан"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['items_formset'] = NariadItemFormSet(self.request.POST, prefix='items')
            context['workers_formset'] = NariadItemFisFormSet(self.request.POST, prefix='workers')
        else:
            context['items_formset'] = NariadItemFormSet(prefix='items')
            context['workers_formset'] = NariadItemFisFormSet(prefix='workers')
        
        # Добавляем HTML пустых форм
        context['empty_item_html'] = render_to_string('includes/empty_row_nariad.html', {
            'form': context['items_formset'].empty_form
        })
        context['empty_worker_html'] = render_to_string('includes/empty_row_worker.html', {
            'form': context['workers_formset'].empty_form
        })
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        items_formset = context['items_formset']
        workers_formset = context['workers_formset']
        
        if items_formset.is_valid() and workers_formset.is_valid():
            self.object = form.save()
            items_formset.instance = self.object
            items_formset.save()
            workers_formset.instance = self.object
            workers_formset.save()
            return super().form_valid(form)
        else:
            return self.render_to_response(self.get_context_data(form=form))

class NariadUpdateView(SuccessMessageMixin, UpdateView):
    model = Nariad
    form_class = NariadForm
    template_name = 'nariads/edit.html'
    success_url = reverse_lazy('nariads:list')
    success_message = "Изменения сохранены"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['items_formset'] = NariadItemFormSet(self.request.POST, instance=self.object, prefix='items')
            context['workers_formset'] = NariadItemFisFormSet(self.request.POST, instance=self.object, prefix='workers')
        else:
            context['items_formset'] = NariadItemFormSet(instance=self.object, prefix='items')
            context['workers_formset'] = NariadItemFisFormSet(instance=self.object, prefix='workers')
        
        # Добавляем HTML пустых форм
        context['empty_item_html'] = render_to_string('includes/empty_row_nariad.html', {
            'form': context['items_formset'].empty_form
        })
        context['empty_worker_html'] = render_to_string('includes/empty_row_worker.html', {
            'form': context['workers_formset'].empty_form
        })
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        items_formset = context['items_formset']
        workers_formset = context['workers_formset']
        
        if items_formset.is_valid() and workers_formset.is_valid():
            self.object = form.save()
            items_formset.instance = self.object
            items_formset.save()
            workers_formset.instance = self.object
            workers_formset.save()
            return super().form_valid(form)
        else:
            return self.render_to_response(self.get_context_data(form=form))

class NariadDeleteView(DeleteView):
    model = Nariad
    success_url = reverse_lazy('nariads:list')
    template_name = 'nariads/delete.html'

    def post(self, request, *args, **kwargs):
        try:
            return self.delete(request, *args, **kwargs)
        except ProtectedError:
            messages.error(request, 'Невозможно удалить: наряд используется в других документах.')
            return HttpResponseRedirect(self.success_url)

class NariadDetailView(DetailView):
    model = Nariad
    template_name = 'nariads/view.html'
    context_object_name = 'nariad'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['items'] = self.object.items.all()
        context['workers'] = self.object.workers.select_related('fio')
        return context