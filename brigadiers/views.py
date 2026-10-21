from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from .models import Brigadier
from .forms import BrigadierForm

class BrigadierListView(ListView):
    model = Brigadier
    template_name = 'brigadier/list.html'
    context_object_name = 'brigadiers'

    def get_queryset(self):
        return Brigadier.objects.select_related('pos').order_by('last_name')

class BrigadierCreateView(CreateView):
    model = Brigadier
    form_class = BrigadierForm
    template_name = 'brigadier/create.html'
    success_url = reverse_lazy('brigadier:list')

class BrigadierUpdateView(UpdateView):
    model = Brigadier
    form_class = BrigadierForm
    template_name = 'brigadier/edit.html'
    success_url = reverse_lazy('brigadier:list')

class BrigadierDeleteView(DeleteView):
    model = Brigadier
    template_name = 'brigadier/delete.html'
    success_url = reverse_lazy('brigadier:list')