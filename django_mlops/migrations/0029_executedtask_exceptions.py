# Generated by Django 5.0.2 on 2024-02-25 21:56

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('django_mlops', '0028_remove_executedtask_task_status_executedtask_status'),
    ]

    operations = [
        migrations.AddField(
            model_name='executedtask',
            name='exceptions',
            field=models.JSONField(default=dict),
        ),
    ]
