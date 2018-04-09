from django import forms

from .models import UserRequest

class RequestForm(forms.ModelForm):

    class Meta:
        model = UserRequest
        fields = ('username', 'from_date', 'to_date', 'city', 'parser', 'test_url')


class TaskForm(forms.Form):
    """ A simple form to read a url from the user in order to find out its length
    and either run it asynchronously or schedule it schedule_times times,
    every schedule_interval seconds.
    """
    url = forms.CharField(label='URL', max_length=128, help_text='Enter a url (starting with http/https) to start a job that will download it and count its words' )

    def clean(self):
        data = super(TaskForm, self).clean()


