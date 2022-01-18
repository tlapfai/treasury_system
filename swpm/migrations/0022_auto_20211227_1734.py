# Generated by Django 3.2.9 on 2021-12-27 09:34

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('swpm', '0021_auto_20211224_2127'),
    ]

    operations = [
        migrations.AddField(
            model_name='irtermstructure',
            name='ref_curve',
            field=models.CharField(blank=True, max_length=16, null=True),
        ),
        migrations.AlterUniqueTogether(
            name='fxvolatility',
            unique_together={('ref_date', 'ccy_pair')},
        ),
        migrations.RemoveField(
            model_name='fxvolatility',
            name='vol',
        ),
    ]