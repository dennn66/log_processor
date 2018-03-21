import requests
from .models import Task
from rq import get_current_job
from django_rq import job


@job
def get_url_words(url):
    # This creates a Task instance to save the job instance and job result
    job = get_current_job()

    task = Task.objects.create(
        job_id=job.get_id(),
        name=url
    )
    response = requests.get(url)
    task.result = len(response.text)
    task.save()
    return task.result
