# Generated by Django 3.2.9 on 2021-11-06 10:41

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('swpm', '0006_auto_20211106_1543'),
    ]

    operations = [
        migrations.AlterField(
            model_name='swapleg',
            name='trade',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='legs', to='swpm.swap'),
        ),
    ]