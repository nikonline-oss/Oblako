from django import forms
from django.forms import inlineformset_factory
from .models import Nariad, NariadItem, NariadItemFis

class NariadForm(forms.ModelForm):
    class Meta:
        model = Nariad
        fields = [
            'organization', 'brigadier', 'responsible', 
            'issued_man', 'received', 'rationer', 
            'date_of_issue', 'evaluation'
        ]
        widgets = {
            'date_of_issue': forms.DateInput(attrs={'type': 'date', 'class': 'datepicker'}),
        }

class NariadItemForm(forms.ModelForm):
    class Meta:
        model = NariadItem
        fields = [
            'date', 'describer', 'category', 'unit_time', 
            'end_time', 'amount', 'price', 'fulfil_time', 'fulfil_day'
        ]
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'datepicker'}),
        }

class NariadItemFisForm(forms.ModelForm):
    class Meta:
        model = NariadItemFis
        fields = [
            'fio', 'category', 'razriad', 'tabel_num', 
            'worked_hour', 'worked_day', 'summa'
        ]

# Создаем формсеты
NariadItemFormSet = inlineformset_factory(
    Nariad,
    NariadItem,
    form=NariadItemForm,
    extra=1,
    can_delete=True
)

NariadItemFisFormSet = inlineformset_factory(
    Nariad,
    NariadItemFis,
    form=NariadItemFisForm,
    extra=1,
    can_delete=True
)