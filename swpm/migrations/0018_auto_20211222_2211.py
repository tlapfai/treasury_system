# Generated by Django 3.2.9 on 2021-12-22 14:11

import datetime
from django.db import migrations, models
import django.db.models.deletion
import swpm.models


class Migration(migrations.Migration):

    dependencies = [
        ('swpm', '0017_auto_20211121_1617'),
    ]

    operations = [
        migrations.AlterField(
            model_name='fxo',
            name='buy_sell',
            field=models.CharField(choices=[('B', 'Buy'), ('S', 'Sell')], default='B', max_length=1),
        ),
        migrations.AlterField(
            model_name='trade',
            name='trade_date',
            field=models.DateField(default=datetime.date.today),
        ),
        migrations.CreateModel(
            name='FXVolatilityQuote',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('ref_date', models.DateField()),
                ('tenor', models.CharField(max_length=6)),
                ('delta', models.FloatField()),
                ('vol', models.FloatField(validators=[swpm.models.validate_positive])),
                ('t', models.DateField()),
                ('surface', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='quotes', to='swpm.fxvolatility')),
            ],
        ),
    ]
