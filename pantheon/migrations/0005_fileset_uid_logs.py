# Generated by Django 2.0.4 on 2018-05-23 22:26

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pantheon', '0004_fileset_perf_file'),
    ]

    operations = [
        migrations.AddField(
            model_name='fileset',
            name='uid_logs',
            field=models.URLField(default=None),
            preserve_default=False,
        ),
    ]
