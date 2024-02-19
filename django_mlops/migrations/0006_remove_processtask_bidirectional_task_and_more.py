# Generated by Django 5.0.2 on 2024-02-17 10:26

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('django_mlops', '0005_rename_nested_task_processtask_bidirectional_task'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='processtask',
            name='bidirectional_task',
        ),
        migrations.AddField(
            model_name='processtask',
            name='bidirectional_dependencies',
            field=models.ManyToManyField(blank=True, related_name='+', to='django_mlops.processtask'),
        ),
    ]
