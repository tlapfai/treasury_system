# Generated by Django 3.2.9 on 2022-01-27 12:17

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('swpm', '0029_alter_fxvolatilityquote_delta'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='RateQuote',
            new_name='InterestRateQuote',
        ),
    ]