# Generated by Django 2.2.5 on 2021-10-26 14:26

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('swpm', '0003_auto_20211024_2155'),
    ]

    operations = [
        migrations.CreateModel(
            name='Calendar',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=16)),
            ],
        ),
        migrations.CreateModel(
            name='RateIndex',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=16)),
            ],
        ),
        migrations.AddField(
            model_name='ccy',
            name='fixing_days',
            field=models.PositiveIntegerField(default=2),
        ),
        migrations.AlterField(
            model_name='ccypair',
            name='base_ccy',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='as_base_ccy', to='swpm.Ccy'),
        ),
        migrations.AlterField(
            model_name='ccypair',
            name='quote_ccy',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='as_quote_ccy', to='swpm.Ccy'),
        ),
        migrations.CreateModel(
            name='RateQuote',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=16)),
                ('rate', models.FloatField()),
                ('tenor', models.CharField(max_length=5)),
                ('type', models.CharField(max_length=5)),
                ('day_counter', models.CharField(max_length=5)),
                ('ccy', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='rates', to='swpm.Ccy')),
            ],
        ),
        migrations.CreateModel(
            name='IRTermStructure',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=16)),
                ('ref_date', models.DateField()),
                ('rates', models.ManyToManyField(related_name='ts', to='swpm.RateQuote')),
            ],
        ),
        migrations.CreateModel(
            name='FXVolatility',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('ref_date', models.DateField()),
                ('vol', models.FloatField()),
                ('ccy_pair', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='vol', to='swpm.CcyPair')),
            ],
        ),
        migrations.AddField(
            model_name='ccypair',
            name='cdr',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='ccy_pair', to='swpm.Calendar'),
        ),
    ]
