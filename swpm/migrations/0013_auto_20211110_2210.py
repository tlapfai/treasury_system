# Generated by Django 3.2.9 on 2021-11-10 14:10

import datetime
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('swpm', '0012_auto_20211109_2020'),
    ]

    operations = [
        migrations.AddField(
            model_name='irtermstructure',
            name='ccy',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='all_curves', to='swpm.ccy'),
        ),
        migrations.AlterField(
            model_name='fxo',
            name='maturity_date',
            field=models.DateField(default=datetime.date(2021, 11, 10)),
        ),
        migrations.AlterField(
            model_name='swapleg',
            name='effective_date',
            field=models.DateField(default=datetime.date(2021, 11, 10)),
        ),
    ]
