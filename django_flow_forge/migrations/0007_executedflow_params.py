# Generated by Django 5.0.4 on 2024-04-08 19:49

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('django_flow_forge', '0006_flowtask_code_flowtask_docstring'),
    ]

    operations = [
        migrations.AddField(
            model_name='executedflow',
            name='params',
            field=models.JSONField(blank=True, default=dict, null=True),
        ),
    ]