# Generated by Django 3.2.9 on 2022-02-06 05:10

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('swpm', '0034_fxo_exercise_type'),
    ]

    operations = [
        migrations.AddField(
            model_name='fxo',
            name='barrier_end',
            field=models.DateField(null=True),
        ),
        migrations.AddField(
            model_name='fxo',
            name='barrier_start',
            field=models.DateField(null=True),
        ),
        migrations.AddField(
            model_name='fxo',
            name='exercise_end',
            field=models.DateField(null=True),
        ),
        migrations.AddField(
            model_name='fxo',
            name='exercise_start',
            field=models.DateField(null=True),
        ),
        migrations.AlterField(
            model_name='fxo',
            name='exercise_type',
            field=models.CharField(choices=[('EUR', 'European'), ('AME', 'American')], max_length=5),
        ),
        migrations.AlterField(
            model_name='fxo',
            name='payoff_type',
            field=models.CharField(choices=[('VAN', 'Vanilla'), ('DIG', 'Digital'), ('BAR', 'Barrier')], max_length=5),
        ),
    ]
