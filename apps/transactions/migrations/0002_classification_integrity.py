from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("transactions", "0001_initial"),
        ("categories", "0002_owner_integrity_and_defaults"),
    ]
    operations = [
        migrations.RunSQL(
            "ALTER TABLE transactions_transaction ADD CONSTRAINT transaction_category_owner_type_fk "
            "FOREIGN KEY (category_id, user_id, type) REFERENCES categories_category (id, user_id, type)",
            "ALTER TABLE transactions_transaction DROP CONSTRAINT transaction_category_owner_type_fk",
        ),
        migrations.RunSQL(
            "ALTER TABLE transactions_transaction ADD CONSTRAINT transaction_subcategory_category_owner_fk "
            "FOREIGN KEY (subcategory_id, category_id, user_id) REFERENCES categories_subcategory (id, category_id, user_id)",
            "ALTER TABLE transactions_transaction DROP CONSTRAINT transaction_subcategory_category_owner_fk",
        ),
    ]
