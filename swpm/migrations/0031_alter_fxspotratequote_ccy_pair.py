# Generated by Django 3.2.9 on 2022-01-27 12:21

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('swpm', '0030_rename_ratequote_interestratequote'),
    ]

    operations = [
        migrations.AlterField(
            model_name='fxspotratequote',
            name='ccy_pair',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='quotes', to='swpm.ccypair'),
        ),
    ]
