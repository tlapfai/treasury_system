# Generated by Django 3.2.9 on 2022-02-17 09:54

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('swpm', '0055_auto_20220213_1615'),
    ]

    operations = [
        migrations.AddField(
            model_name='fxo',
            name='subtype',
            field=models.CharField(blank=True, choices=[('VAN', 'VAN'), ('AME', 'AME'), ('DOUB_KO', 'DOUB_KO'), ('DOUB_KI', 'DOUB_KI'), ('KIKO', 'KIKO'), ('KOKI', 'KOKI')], editable=False, max_length=8, null=True),
        ),
    ]
