# Generated by Django 3.2.9 on 2021-11-19 04:45

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('swpm', '0002_auto_20211119_1020'),
    ]

    operations = [
        migrations.RenameField(
            model_name='ccy',
            old_name='cdr',
            new_name='calendar',
        ),
        migrations.RemoveField(
            model_name='ccypair',
            name='cdr',
        ),
    ]