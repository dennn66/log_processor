import django_tables2 as tables
from django_tables2.utils import A  # alias for Accessor

from django.utils.safestring import mark_safe
from .models import UserRequest

from django.conf.urls.static import static
from django.conf import settings
import os


from rq import Queue
from django_rq import get_connection
from sys import platform
from rq.job import Job


class UserRequestTable(tables.Table):
    edit = tables.LinkColumn('request_edit', text='Edit', args=[A('pk')], orderable=False, empty_values=())
    delete = tables.LinkColumn('request_delete', text='Delete', args=[A('pk')], orderable=False, empty_values=())
    # еще нужные поля

    class Meta:
        empty_text = u'Объекты, удовлетворяющие критериям поиска, не найдены...'
        model = UserRequest
        attrs = {'class': 'paleblue'}
        sequence = ('created', 	'city', 	'username', 	'from_date', 	'to_date', 	'parser', 	'author', 'filename') # тут столбцы, выводимые в таблицу
        exclude = 'id'

    def render_filename(self, value, record):
        url = static('cloud-download.png')

        if platform != "win32":
            try:
                ret = {'status': 'test'}
                redis_conn = get_connection()
                job_id = record.job_id
                q = Queue(connection=redis_conn)
                job = q.fetch_job(job_id)
                #job = Job.fetch(job_id, redis_conn)  # fetch Job from redis

                if job.is_finished:
                    ret = {'status': 'ready'}
                elif job.is_queued:
                    ret = {'status': 'in-queue'}
                elif job.is_started:
                    ret = {'status': 'running...'}
                elif job.is_failed:
                    ret = {'status': 'failed'}

            except BaseException as e:
                ret = {'status':  'starting...'}
        else:
            ret = {'status': value}

        if(value == 'none'):
            return mark_safe(ret['status'])
        else:
            conf = record.get_config()
            tmp_path = conf['tmp_path']
            href = os.path.join(settings.MEDIA_URL, os.path.relpath(os.path.join(tmp_path, value), settings.MEDIA_ROOT))
            return mark_safe('<a href="' + href + '">' + ret['status'] + '</a>')
            #return mark_safe('<a href="' + href + '"><img src="' + url + '"></a>')
