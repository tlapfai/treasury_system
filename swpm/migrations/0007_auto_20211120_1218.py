# Generated by Django 3.2.9 on 2021-11-20 04:18

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('swpm', '0006_ccypair_calendar'),
    ]

    operations = [
        migrations.AlterField(
            model_name='irtermstructure',
            name='as_fx_curve',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='fx_curve', to='swpm.ccy'),
        ),
        migrations.AlterField(
            model_name='irtermstructure',
            name='as_rf_curve',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='rf_curve', to='swpm.ccy'),
        ),
    ]