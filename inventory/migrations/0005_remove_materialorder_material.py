# Generated by Django 5.2.1 on 2025-05-30 06:56

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0004_alter_materialorder_total_cost'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='materialorder',
            name='material',
        ),
    ]
