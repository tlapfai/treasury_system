# Generated by Django 3.2.9 on 2022-02-12 06:55

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('swpm', '0042_auto_20220209_2158'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='fxobarrierdetail',
            name='trade',
        ),
        migrations.AddField(
            model_name='cashflow',
            name='value_date',
            field=models.DateField(null=True),
        ),
        migrations.AlterField(
            model_name='cashflow',
            name='amount',
            field=models.DecimalField(decimal_places=2, max_digits=32),
        ),
        migrations.AlterField(
            model_name='cashflow',
            name='trade',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='cashflows', to='swpm.trade'),
        ),
        migrations.AlterField(
            model_name='fxobarrierdetail',
            name='payoff_at_hit',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='fxobarrierdetail',
            name='rebate_at_hit',
            field=models.BooleanField(default=False),
        ),
    ]
