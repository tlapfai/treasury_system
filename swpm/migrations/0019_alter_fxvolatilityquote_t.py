# Generated by Django 3.2.9 on 2021-12-22 14:14

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('swpm', '0018_auto_20211222_2211'),
    ]

    operations = [
        migrations.AlterField(
            model_name='fxvolatilityquote',
            name='t',
            field=models.DateField(auto_created=True),
        ),
    ]
