# Generated by Django 5.0.2 on 2024-02-17 11:28

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('django_flow_forge', '0008_rename_dependencies_processtask_depends_on'),
    ]

    operations = [
        migrations.CreateModel(
            name='ProcessRun',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('start_time', models.DateTimeField(auto_now_add=True)),
                ('end_time', models.DateTimeField(blank=True, null=True)),
                ('executed_by', models.CharField(blank=True, max_length=255, null=True)),
                ('process', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='runs', to='django_flow_forge.process')),
            ],
        ),
        migrations.CreateModel(
            name='TaskRun',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('task_snapshot', models.JSONField(default=dict)),
                ('output', models.JSONField(default=dict)),
                ('start_time', models.DateTimeField(auto_now_add=True)),
                ('end_time', models.DateTimeField(blank=True, null=True)),
                ('process_run', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='task_runs', to='django_flow_forge.processrun')),
                ('task', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='runs', to='django_flow_forge.processtask')),
            ],
        ),
    ]