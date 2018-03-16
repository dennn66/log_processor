from django.shortcuts import render, get_object_or_404
from .models import City, Collector, Source, Settings, Parser, RadiusAttributeValue, RadiusAttributeType, Dim, Counter, Index, TrafficType, TrafficSummary, UserRequest
from .forms import RequestForm
from .tables import UserRequestTable
from django.shortcuts import redirect
from django.utils import timezone as tz
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login
from django.contrib.messages import constants as messages
from django.core.files import File
from django.core.files.storage import FileSystemStorage
import os
from django.conf import settings



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

def test(request, pk):
    user_request = get_object_or_404(UserRequest, pk=pk)
    f = open('logparser/views.py')
    user_request.filename.save(str('logparser/tests.py'), File(f))
    return redirect('request_list')

def rqst_many_upd(request):
    action = request.POST.get('action')
    arr = [request.POST.get(key) for key in request.POST.keys() if u'check_column' in key]
    qs = UserRequest.objects.filter(pk__in=arr)
    if action == u'done':
        rows_updated = qs.update(username=u'done', created=tz.now())
        #msg = u'Количество заявок, отмеченных как исполненные - {}.'
    elif action == u'cancel':
        rows_updated = qs.update(username=u'cancel', created=tz.now())
        #msg = u'Количество заявок, отмеченных как отменённые - {}.'
    else:
        #messages.WARNING(request, u'Недопустимое действие.')
        return redirect('request_list')
    #messages.SUCCESS(request, msg.format(rows_updated))
    return redirect('request_list')

@login_required
def request_detail(request, pk):
    user_request  = get_object_or_404(UserRequest, pk=pk)
    return render(request, 'logparser/request_detail.html', context={'request': user_request})

@login_required
def request_new(request):
    if request.method == "POST":
        form = RequestForm(request.POST)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            post.created = tz.now()
            post.save()
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
            user_request = form.save(commit=False)
            user_request.author = request.user
            user_request.created = tz.now()
            user_request.filename.delete()
            user_request.save()
            return redirect('request_list')
    else:
        form = RequestForm(instance=user_request)
        return render(request, 'logparser/request_edit.html', context={'form': form, 'request': user_request})


@login_required
def request_delete(request, pk):
    user_request = get_object_or_404(UserRequest, pk=pk)
    return render(request, 'logparser/request_delete.html', context={'request': user_request})

def request_do_delete(request, pk):
    user_request = get_object_or_404(UserRequest, pk=pk)
    user_request.filename.delete()
    user_request.delete()
    return redirect('request_list')