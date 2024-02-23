# Generated by Django 5.0.2 on 2024-02-23 20:08

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('django_mlops', '0021_alter_executedprocess_process_id_snapshot_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='executedprocess',
            name='status',
            field=models.CharField(choices=[('complete', 'Complete'), ('still_running', 'Still Running'), ('failed', 'Failed')], default='still_running', max_length=20),
        ),
    ]
