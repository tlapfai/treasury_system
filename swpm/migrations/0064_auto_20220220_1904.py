# Generated by Django 3.2.9 on 2022-02-20 11:04

from django.db import migrations, models
import swpm.models


class Migration(migrations.Migration):

    dependencies = [
        ('swpm', '0063_alter_swapleg_notional'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='rateindex',
            name='index',
        ),
        migrations.AlterField(
            model_name='rateindex',
            name='tenor',
            field=models.CharField(max_length=16, validators=[swpm.models.validate_period]),
        ),
    ]
