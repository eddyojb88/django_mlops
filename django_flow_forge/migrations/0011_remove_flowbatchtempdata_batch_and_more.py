# Generated by Django 5.0 on 2024-04-14 15:26

import django.core.serializers.json
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('django_flow_forge', '0010_batchhandler'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='flowbatchtempdata',
            name='batch',
        ),
        migrations.RemoveField(
            model_name='batchhandler',
            name='executed_flows',
        ),
        migrations.RemoveField(
            model_name='batchhandler',
            name='flow',
        ),
        migrations.RemoveField(
            model_name='executedflow',
            name='executed_tasks',
        ),
        migrations.AddField(
            model_name='batchhandler',
            name='batch_ref_name',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='executedflow',
            name='batch_handler',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='executed_flows', to='django_flow_forge.batchhandler'),
        ),
        migrations.CreateModel(
            name='BatchTempData',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('batch_index', models.IntegerField(default=0)),
                ('temp_data', models.JSONField(default=dict, encoder=django.core.serializers.json.DjangoJSONEncoder, null=True)),
                ('batch_handler', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='batch_temp_data', to='django_flow_forge.batchhandler')),
            ],
        ),
        migrations.DeleteModel(
            name='FlowBatch',
        ),
        migrations.DeleteModel(
            name='FlowBatchTempData',
        ),
    ]
