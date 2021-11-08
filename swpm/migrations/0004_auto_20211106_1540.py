# Generated by Django 3.2.8 on 2021-11-06 07:40

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('swpm', '0003_auto_20211106_1503'),
    ]

    operations = [
        migrations.AlterField(
            model_name='fxo',
            name='notional_1',
            field=models.DecimalField(decimal_places=2, max_digits=20, validators=[django.core.validators.MinValueValidator(0.01), django.core.validators.DecimalValidator(decimal_places=2, max_digits=20)]),
        ),
        migrations.AlterField(
            model_name='fxo',
            name='notional_2',
            field=models.DecimalField(decimal_places=2, max_digits=20),
        ),
        migrations.AlterField(
            model_name='fxo',
            name='strike_price',
            field=models.DecimalField(decimal_places=4, max_digits=20, validators=[django.core.validators.MinValueValidator(0.0001)]),
        ),
    ]