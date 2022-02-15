# Generated by Django 3.2.9 on 2022-02-08 13:05

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('swpm', '0038_auto_20220208_2058'),
    ]

    operations = [
        migrations.AddField(
            model_name='ccy',
            name='fx_curve',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='as_fx_curve', to='swpm.irtermstructure'),
        ),
        migrations.AddField(
            model_name='ccy',
            name='rf_curve',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='as_rf_curve', to='swpm.irtermstructure'),
        ),
    ]