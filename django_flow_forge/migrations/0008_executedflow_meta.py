# Generated by Django 5.0 on 2024-04-13 21:24

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('django_flow_forge', '0007_executedflow_params'),
    ]

    operations = [
        migrations.AddField(
            model_name='executedflow',
            name='meta',
            field=models.JSONField(blank=True, default=dict, null=True),
        ),
    ]
