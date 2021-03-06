# Generated by Django 2.1.7 on 2019-04-05 14:39

from django.db import migrations, models

import registrations.validators


class Migration(migrations.Migration):

    initial = True

    dependencies: list = []

    operations = [
        migrations.CreateModel(
            name="ReferralLink",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "msisdn",
                    models.CharField(
                        help_text=(
                            "The MSISDN of the user who referred the current "
                            "registration"
                        ),
                        max_length=12,
                        unique=True,
                        validators=[registrations.validators.msisdn_validator],
                        verbose_name="MSISDN",
                    ),
                ),
            ],
        )
    ]
