import requests
from .models import Task, UserRequest
from rq import get_current_job
from django_rq import job


@job
def get_url_words(task : Task):
    # This creates a Task instance to save the job instance and job result
    job = get_current_job()
    task.job_id = job.get_id()
    response = requests.get(task.name)
    task.result = len(response.text)
    task.save()
    return task.result


@job
def get_request_result(url):
    # This creates a Task instance to save the job instance and job result
    job = get_current_job()

    task = UserRequest.objects.create(
        job_id=job.get_id(),
        name=url
    )
    response = requests.get(url)
    task.result = len(response.text)
    task.save()
    return task.result


    # city, parser, author, username, from_date, to_date, created, filename, test_url