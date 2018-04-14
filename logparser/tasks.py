import requests
from .models import  UserRequest
from rq import get_current_job
from django_rq import job
from sys import platform
from .raw_accounting_parser import Parser
import os
from django.conf import settings as app_settings

@job
def get_request_result(task : UserRequest):
    # This creates a Task instance to save the job instance and job result
    if platform != "win32":
        job = get_current_job()
        task.job_id=job.get_id()
    task.save()
    conf = task.get_config()
    tmp_path = conf['tmp_path']
    parser = Parser(task.get_config(), task.get_request())
    parser.read_data()
    filename = parser.save()
    if filename != None and filename != '':
        task.filename = os.path.relpath(filename, tmp_path)
    else:
        task.filename = ''
    task.save()
    return task.filename


    # city, parser, author, username, from_date, to_date, created, filename, test_url