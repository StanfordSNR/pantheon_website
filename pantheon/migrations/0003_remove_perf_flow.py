# Generated by Django 2.0.5 on 2018-05-21 04:33

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('pantheon', '0002_auto_20180504_2325'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='perf',
            name='flow',
        ),
    ]
