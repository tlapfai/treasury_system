# Generated by Django 3.2.9 on 2021-11-08 14:47

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('swpm', '0010_auto_20211108_2139'),
    ]

    operations = [
        migrations.AddField(
            model_name='ccy',
            name='foreign_exchange_curve',
            field=models.CharField(blank=True, max_length=16, null=True),
        ),
        migrations.AddField(
            model_name='ccy',
            name='risk_free_curve',
            field=models.CharField(blank=True, max_length=16, null=True),
        ),
    ]