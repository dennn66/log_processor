from django.shortcuts import render, get_object_or_404
from .models import  UserRequest
from .forms import RequestForm
from .tables import UserRequestTable
from django.shortcuts import redirect
from django.utils import timezone as tz
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login
from django.core.files import File

from .tasks import  get_request_result
from sys import platform

from rq.job import Job
import django_rq



# Create your views here.
# Подробнее о QuerySets в Django можно узнать в официальной документации: https://docs.djangoproject.com/en/1.11/ref/models/querysets/


def login(request):
    username = request.POST.get('username')
    password = request.POST.get('password')
    user = authenticate(request, username=username, password=password)
    if user is not None:
        if user.is_active:
            login(request, user)
            return redirect('/')
    return render(request, 'logparser/../templates/registration/login.html', context = {})

@login_required
def request_list(request):
    order_by = request.GET.get('sort', 'created')
    table = UserRequestTable(UserRequest.objects.all().order_by(order_by))
    return render(request, 'logparser/list.html', {'table': table})


@login_required
def request_detail(request, pk):
    user_request  = get_object_or_404(UserRequest, pk=pk)
    return render(request, 'logparser/request_detail.html', context={'request': user_request})

@login_required
def request_new(request):
    if request.method == "POST":
        form = RequestForm(request.POST)
        if form.is_valid():
            task = form.save(commit=False)
            task.author = request.user
            task.created = tz.now()
            task.result = 'waiting...'
            task.job_id = 'none'
            task.filename = ''
            task.save()
            if platform != "win32":
                get_request_result.delay(task)
            else:
                get_request_result(task)
            return redirect('request_list')
    else:
        form = RequestForm()
    return render(request, 'logparser/request_create.html', {'form': form})


@login_required
def request_edit(request, pk):
    user_request = get_object_or_404(UserRequest, pk=pk)
    if request.method == "POST":
        form = RequestForm(request.POST, instance=user_request)
        if form.is_valid():
            task = form.save(commit=False)
            task.author = request.user
            task.created = tz.now()
            task.filename = ''
            #task.filename.delete()
            task.job_id = 'none'
            task.save()
            if platform != "win32":
                get_request_result.delay(task)
            else:
                get_request_result(task)
            return redirect('request_list')
    else:
        form = RequestForm(instance=user_request)
        return render(request, 'logparser/request_edit.html', context={'form': form, 'request': user_request})


@login_required
def request_delete(request, pk):
    user_request = get_object_or_404(UserRequest, pk=pk)
    return render(request, 'logparser/request_delete.html', context={'request': user_request})

@login_required
def request_do_delete(request, pk):
    user_request = get_object_or_404(UserRequest, pk=pk)
    #user_request.filename.delete()
    user_request.delete()
    return redirect('request_list')
