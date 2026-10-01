from django.db import transaction
from .models import Category, Subcategory

DEFAULT_CATEGORIES = {
    "DESPESA": {
        "Alimentação": ["Mercado", "Restaurante", "Padaria", "Delivery"],
        "Moradia": ["Aluguel", "Água", "Energia", "Internet"],
        "Transporte": ["Combustível", "Transporte por aplicativo", "Transporte público", "Manutenção"],
        "Lazer": ["Passeios", "Assinaturas", "Entretenimento"],
    },
    "RECEITA": {
        "Trabalho": ["Venda", "Serviço", "Comissão"],
        "Pessoal": ["Venda de bem", "Outros recebimentos"],
    },
}


@transaction.atomic
def create_defaults(user):
    for movement_type, categories in DEFAULT_CATEGORIES.items():
        for name, names in categories.items():
            category, _ = Category.objects.get_or_create(user=user, name=name, type=movement_type)
            for subname in names:
                Subcategory.objects.get_or_create(user=user, category=category, name=subname)
