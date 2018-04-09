from django.utils import timezone as tz
from django.core.files import File
from django.db import models
import requests
from rq import get_current_job

# Create your models here.

'''''''''
Sources Model
'''''''''

class City(models.Model):
    #author = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    name = models.CharField(max_length=20)
    timezone = models.CharField(max_length=20)
    #comment = models.TextField()
    created_date = models.DateTimeField(default=tz.now)

    def get_config(self):
        collectors_obj = Collector.objects.filter(city=self)
        collector_hosts = []
        bras_sources = []
        for collector in collectors_obj:
            collector_hosts += [collector.ip]
            logpath = collector.logpath
            sources = Source.objects.filter(collector = collector)
            for source in sources:
                bras_sources += [source.ip]

        bras_sources = set(bras_sources)

        collectors = [ {'collectors':{self.name:
                         {'timezone': self.timezone,
                         'collector_host': collector_hosts,
                         'bras_sources': bras_sources,
                         'logpath' : logpath
                         }
                      }}]
        return collectors

    def __str__(self):
        return self.name

class Collector (models.Model):
    #author = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    city = models.ForeignKey('City',  on_delete=models.CASCADE)
    ip = models.CharField(max_length=20)
    logpath = models.CharField(default='/opt/fr.krus/acct/', max_length=200)

    def __str__(self):
        return self.ip

class Source (models.Model):
    #author = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    collector = models.ForeignKey('Collector', on_delete=models.CASCADE)
    ip = models.CharField(max_length=20)


    def __str__(self):
        return self.ip + ' (' + str(self.collector) + ')'

class Settings(models.Model):
    name = models.CharField(default='default', max_length=200)
    ssh_username = models.CharField(max_length=20)
    ssh_key = models.CharField(default='../key', max_length=200)
    radius_log_path = models.CharField(default='../radius-logs', max_length=200)
    tmp_path = models.CharField(default='../tmp', max_length=200)
    log_path = models.CharField(default='../log', max_length=200)

    def get_config(self):
        settings = [
            {'ssh_user': {'privatekeyfile': self.ssh_key, 'username': self.ssh_username}},
            {'radius_log_path': self.radius_log_path},
            {'tmp_path': self.tmp_path},
            {'log_path': self.log_path},
        ]
        return settings


    def __str__(self):
        return self.name


'''''''''
Parser model
'''''''''
class Parser(models.Model):
    name = models.CharField(default='Internet on BRAS', max_length=200)

    def get_config(self):
        tags_obj = RadiusAttributeValue.objects.filter(parser=self)
        tags = []
        for tag in tags_obj:
            tags += [{tag.tag : tag.name.name}]

        dim_obj = Dim.objects.filter(parser=self)
        dims = []
        for dim in dim_obj:
            dims += [dim.name]

        cnt_obj = Counter.objects.filter(parser=self)
        counters = []
        for cnt in cnt_obj:
            counters += [cnt.name]

        indx_obj = Index.objects.all() #filter(parser=self)
        index = []
        for indx in indx_obj:
            index += [indx.name]

        trf_obj = TrafficType.objects.filter(parser=self)
        traffic_types = []
        for trf in trf_obj:
            traffic_types += [{trf.type_id: trf.name}]

        tsum_obj = TrafficSummary.objects.filter(parser=self)
        traffic_summary = []
        for tsum in tsum_obj:
            traffic_summary += [tsum.name]

        parser_config = { 'tags' : tags,
                          'counters': counters,
                          'index' : index,
                          'dims': dims,
                          'traffic_types' :traffic_types,
                          'traffic_summary': traffic_summary}

        return [{'parser_config': parser_config}]

    def __str__(self):
        return self.name

class RadiusAttributeType(models.Model):
    name = models.CharField(default='none', max_length=200)
    parser = models.ForeignKey('Parser',  on_delete=models.CASCADE)

    def __str__(self):
        return self.name

class RadiusAttributeValue(models.Model):
    name = models.ForeignKey('RadiusAttributeType', on_delete=models.CASCADE)
    parser = models.ForeignKey('Parser',  on_delete=models.CASCADE)
    tag = models.CharField(default='none', max_length=200)
    def __str__(self):
        return str(self.tag) + ' (' + str(self.name) + ')'

class Dim(models.Model):
    name = models.ForeignKey('RadiusAttributeType', on_delete=models.CASCADE)
    parser = models.ForeignKey('Parser', on_delete=models.CASCADE)
    def __str__(self):
        return str(self.name)

class Counter(models.Model):
    name = models.ForeignKey('RadiusAttributeType', on_delete=models.CASCADE)
    parser = models.ForeignKey('Parser', on_delete=models.CASCADE)
    def __str__(self):
        return str(self.name)

class Index(models.Model):
    name = models.ForeignKey('RadiusAttributeType', on_delete=models.CASCADE)
    parser = models.ForeignKey('Parser', on_delete=models.CASCADE)
    def __str__(self):
        return str(self.name)

class TrafficType(models.Model):
    name = models.CharField(default='none', max_length=200)
    type_id = models.CharField(default='none', max_length=200)
    parser = models.ForeignKey('Parser', on_delete=models.CASCADE)
    def __str__(self):
        return self.name

class TrafficSummary(models.Model):
    name = models.ForeignKey('TrafficType', on_delete=models.CASCADE)
    parser = models.ForeignKey('Parser', on_delete=models.CASCADE)
    def __str__(self):
        return str(self.name)

'''''''''
Request model
'''''''''

class UserRequest(models.Model):
    city = models.ForeignKey('City',  on_delete=models.CASCADE)
    parser = models.ForeignKey('Parser', on_delete=models.CASCADE)
    author = models.ForeignKey('auth.User', default=0, on_delete=models.CASCADE)
    username = models.CharField(default='', max_length=50, blank=True)
    from_date = models.DateTimeField(default=tz.now)
    to_date = models.DateTimeField(default=tz.now)
    created =  models.DateTimeField(default=tz.now)
    filename = models.FileField(upload_to='user_media',  blank=True)

    test_url = models.CharField(max_length=128, blank=True, null=True)
    job_id = models.CharField(max_length=128, blank=True, null=True)

    def __str__(self):
        return str(self.created)

    def get_config(self):
        settings = Settings.objects.filter(name='default').first()
        config = settings.get_config()
        config += self.city.get_config()
        config += self.parser.get_config()
        return config

    def get_request(self):
        request = {'username': self.username,
                   'from_date': str(self.from_date),
                   'to_date': str(self.to_date),
                   'city': self.city.name,
                   }
        return request

    def run(self):
        print(str(self.get_config()))
        print(str(self.get_request()))



class Task(models.Model):
    # A model to save information about an asynchronous task
    created_on = models.DateTimeField(auto_now_add=True)
    name = models.CharField(max_length=128)
    job_id = models.CharField(max_length=128)
    result = models.CharField(max_length=128, blank=True, null=True)

