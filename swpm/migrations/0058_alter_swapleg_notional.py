# Generated by Django 3.2.9 on 2022-02-20 06:54

from django.db import migrations, models
import swpm.models


class Migration(migrations.Migration):

    dependencies = [
        ('swpm', '0057_auto_20220220_1442'),
    ]

    operations = [
        migrations.AlterField(
            model_name='swapleg',
            name='notional',
            field=models.DecimalField(decimal_places=8, default=100000000.0, max_digits=10, validators=[swpm.models.validate_positive]),
        ),
    ]
