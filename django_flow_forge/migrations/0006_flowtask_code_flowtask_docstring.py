# Generated by Django 5.0 on 2024-03-27 20:56

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('django_flow_forge', '0005_alter_flow_options'),
    ]

    operations = [
        migrations.AddField(
            model_name='flowtask',
            name='code',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='flowtask',
            name='docstring',
            field=models.TextField(blank=True, null=True),
        ),
    ]