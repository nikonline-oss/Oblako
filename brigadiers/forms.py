from django import forms
from .models import Brigadier

class BrigadierForm(forms.ModelForm):
    class Meta:
        model = Brigadier
        fields = [
            'last_name', 'first_name', 'middle_name', 
            'pos', 'passport_series', 'passport_number', 
            'passport_issued_by', 'passport_date_of_issue'
        ]
        widgets = {
            'passport_date_of_issue': forms.DateInput(attrs={'type': 'date'}),
        }