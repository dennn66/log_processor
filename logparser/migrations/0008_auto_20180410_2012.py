# Generated by Django 2.0.3 on 2018-04-10 15:12

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('logparser', '0007_merge_20180329_0220'),
    ]

    operations = [
        migrations.DeleteModel(
            name='Task',
        ),
        migrations.AddField(
            model_name='userrequest',
            name='job_id',
            field=models.CharField(blank=True, max_length=128, null=True),
        ),
        migrations.AddField(
            model_name='userrequest',
            name='result',
            field=models.CharField(blank=True, max_length=128, null=True),
        ),
        migrations.AddField(
            model_name='userrequest',
            name='test_url',
            field=models.CharField(blank=True, max_length=128, null=True),
        ),
    ]