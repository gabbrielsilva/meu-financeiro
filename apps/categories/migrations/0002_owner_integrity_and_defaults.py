from django.conf import settings
from django.db import migrations


def seed_existing_accounts(apps, schema_editor):
    User = apps.get_model(settings.AUTH_USER_MODEL)
    Category = apps.get_model("categories", "Category")
    Subcategory = apps.get_model("categories", "Subcategory")
    defaults = {
        "DESPESA": {
            "Alimentação": ["Mercado", "Restaurante", "Padaria", "Delivery"],
            "Moradia": ["Aluguel", "Água", "Energia", "Internet"],
            "Transporte": ["Combustível", "Transporte por aplicativo", "Transporte público", "Manutenção"],
            "Lazer": ["Passeios", "Assinaturas", "Entretenimento"],
        },
        "RECEITA": {"Trabalho": ["Venda", "Serviço", "Comissão"], "Pessoal": ["Venda de bem", "Outros recebimentos"]},
    }
    alias = schema_editor.connection.alias
    for user in User.objects.using(alias).iterator():
        for kind, categories in defaults.items():
            for name, children in categories.items():
                category, _ = Category.objects.using(alias).get_or_create(user_id=user.pk, type=kind, name=name)
                for child in children:
                    Subcategory.objects.using(alias).get_or_create(user_id=user.pk, category_id=category.pk, name=child)


class Migration(migrations.Migration):
    dependencies = [("categories", "0001_initial")]
    operations = [
        migrations.RunSQL(
            "ALTER TABLE categories_subcategory ADD CONSTRAINT subcategory_category_owner_fk "
            "FOREIGN KEY (category_id, user_id) REFERENCES categories_category (id, user_id)",
            "ALTER TABLE categories_subcategory DROP CONSTRAINT subcategory_category_owner_fk",
        ),
        migrations.RunPython(seed_existing_accounts, migrations.RunPython.noop),
    ]
