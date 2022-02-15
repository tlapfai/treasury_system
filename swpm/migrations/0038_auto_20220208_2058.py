# Generated by Django 3.2.9 on 2022-02-08 12:58

from django.db import migrations, models
import django.db.models.deletion
import swpm.models


class Migration(migrations.Migration):

    dependencies = [
        ('swpm', '0037_rename_vol_fxvolatilityquote_value'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='ccy',
            name='foreign_exchange_curve',
        ),
        migrations.RemoveField(
            model_name='ccy',
            name='risk_free_curve',
        ),
        migrations.RemoveField(
            model_name='irtermstructure',
            name='as_fx_curve',
        ),
        migrations.RemoveField(
            model_name='irtermstructure',
            name='as_rf_curve',
        ),
        migrations.CreateModel(
            name='FXOBarrierDetail',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('barrier_start', models.DateField(blank=True, null=True)),
                ('barrier_end', models.DateField(blank=True, null=True)),
                ('upper_barrier_level', models.FloatField(validators=[swpm.models.validate_positive])),
                ('lower_barrier_level', models.FloatField(validators=[swpm.models.validate_positive])),
                ('rebate', models.FloatField(default=0)),
                ('rebate_at_hit', models.BooleanField()),
                ('payoff_at_hit', models.BooleanField()),
                ('trade', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='swpm.fxo')),
            ],
        ),
        migrations.AlterField(
            model_name='fxo',
            name='barrier_detail',
            field=models.OneToOneField(null=True, on_delete=django.db.models.deletion.CASCADE, to='swpm.fxobarrierdetail'),
        ),
        migrations.DeleteModel(
            name='BarrierDetail',
        ),
    ]