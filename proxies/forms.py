from django import forms
from django.forms import inlineformset_factory
from .models import Proxy, ProxyItem

class ProxyForm(forms.ModelForm):
    class Meta:
        model = Proxy
        fields = ['organization', 'employee', 'customer', 'date_of_issue', 'is_valid_until']
        widgets = {
            'date_of_issue': forms.DateInput(attrs={'type': 'date'}),
            'is_valid_until': forms.DateInput(attrs={'type': 'date'}),
        }

class ProxyItemForm(forms.ModelForm):
    class Meta:
        model = ProxyItem
        fields = ['product', 'amount']

ProxyItemFormSet = inlineformset_factory(
    Proxy,
    ProxyItem,
    form=ProxyItemForm,
    extra=1,
    can_delete=True
)