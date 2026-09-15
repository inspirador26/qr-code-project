import secrets

from django.db import migrations, models

import offers.tokens


def populate_public_tokens(apps, schema_editor):
    Offer = apps.get_model("offers", "Offer")
    offers = Offer.objects.using(schema_editor.connection.alias)
    # Generate per row: AddField's callable default is evaluated only once.
    used = set()
    for offer in offers.all().iterator():
        token = "".join(secrets.choice("23456789ABCDEFGHJKMNPQRSTUVWXYZ") for _ in range(10))
        while token in used:
            token = "".join(secrets.choice("23456789ABCDEFGHJKMNPQRSTUVWXYZ") for _ in range(10))
        used.add(token)
        offers.filter(pk=offer.pk).update(public_token=token)


class Migration(migrations.Migration):
    dependencies = [("offers", "0001_initial")]

    operations = [
        migrations.AddField(
            model_name="offer",
            name="public_token",
            field=models.CharField(max_length=12, null=True, editable=False),
        ),
        migrations.RunPython(populate_public_tokens, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="offer",
            name="public_token",
            field=models.CharField(
                max_length=12, unique=True, db_index=True, editable=False,
                default=offers.tokens.generate_public_token,
            ),
        ),
    ]
