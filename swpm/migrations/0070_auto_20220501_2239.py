# Generated by Django 3.2.9 on 2022-05-01 14:39

from django.db import migrations, models
import django.db.models.deletion
import swpm.models


class Migration(migrations.Migration):

    dependencies = [
        ('swpm', '0069_interestratequote_days_key'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='swapleg',
            name='tenor',
        ),
        migrations.AddField(
            model_name='schedule',
            name='tenor',
            field=models.CharField(blank=True, max_length=8, null=True, validators=[swpm.models.validate_period]),
        ),
        migrations.AddField(
            model_name='swapleg',
            name='gearing',
            field=models.DecimalField(decimal_places=4, default=1.0, max_digits=8),
        ),
        migrations.AlterField(
            model_name='rateindexfixing',
            name='value',
            field=models.DecimalField(decimal_places=8, max_digits=12),
        ),
        migrations.AlterField(
            model_name='swapleg',
            name='index',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='swpm.rateindex'),
        ),
    ]
