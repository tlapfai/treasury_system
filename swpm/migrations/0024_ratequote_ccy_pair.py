# Generated by Django 3.2.9 on 2021-12-30 12:48

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('swpm', '0023_auto_20211228_2238'),
    ]

    operations = [
        migrations.AddField(
            model_name='ratequote',
            name='ccy_pair',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='swpm.ccypair'),
        ),
    ]
