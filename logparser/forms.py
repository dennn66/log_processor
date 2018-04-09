from django import forms

from .models import UserRequest

class RequestForm(forms.ModelForm):

    class Meta:
        model = UserRequest
        fields = ('username', 'from_date', 'to_date', 'city', 'parser', 'test_url')

