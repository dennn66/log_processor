import requests
from .models import  UserRequest
from rq import get_current_job
from django_rq import job


@job
def get_request_result(task : UserRequest):
    # This creates a Task instance to save the job instance and job result
    job = get_current_job()

    task.job_id=job.get_id()
    task.result = 'processing...'
    task.save()
    response = requests.get(task.test_url)
    task.result = len(response.text)
    task.save()
    return task.result


    # city, parser, author, username, from_date, to_date, created, filename, test_url