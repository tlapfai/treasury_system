# Generated by Django 3.2.9 on 2022-02-20 08:13

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('swpm', '0058_alter_swapleg_notional'),
    ]

    operations = [
        migrations.RenameField(
            model_name='schedule',
            old_name='effective_date',
            new_name='start_date',
        ),
        migrations.AlterField(
            model_name='swapleg',
            name='ccy',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='+', to='swpm.ccy'),
        ),
        migrations.AlterField(
            model_name='swapleg',
            name='schedule',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='swpm.schedule'),
        ),
    ]
