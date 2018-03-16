from django.utils import timezone as tz
from django.core.files import File
from django.db import models


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
    def __str__(self):
        return self.name


'''''''''
Parser model
'''''''''
class Parser(models.Model):
    name = models.CharField(default='Internet on BRAS', max_length=200)
    def __str__(self):
        return self.name

class RadiusAttributeType(models.Model):
    name = models.CharField(default='none', max_length=200)

    def __str__(self):
        return self.name

class RadiusAttributeValue(models.Model):
    name = models.ForeignKey('RadiusAttributeType', on_delete=models.CASCADE)
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

    def __str__(self):
        return str(self.created)