# Generated by Django 5.0.6 on 2024-06-21 12:38

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('django_flow_forge', '0015_batchhandler_date_initialised'),
    ]

    operations = [
        migrations.AddField(
            model_name='executedflow',
            name='flow_batch',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='executed_flows', to='django_flow_forge.flowbatch'),
        ),
    ]
