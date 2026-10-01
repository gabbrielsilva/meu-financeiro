from django import forms
from apps.accounts.forms import StyledForm
from .models import Category, MovementType


class CategoryForm(StyledForm):
    name = forms.CharField(label="Nome", max_length=100)
    type = forms.ChoiceField(label="Tipo", choices=MovementType.choices)
    is_active = forms.BooleanField(label="Categoria ativa", required=False, initial=True)

    def __init__(self, *args, instance=None, **kwargs):
        super().__init__(*args, **kwargs)
        if instance:
            self.fields["type"].disabled = True


class SubcategoryForm(StyledForm):
    category = forms.ModelChoiceField(label="Categoria", queryset=Category.objects.none())
    name = forms.CharField(label="Nome", max_length=100)
    is_active = forms.BooleanField(label="Subcategoria ativa", required=False, initial=True)

    def __init__(self, *args, user, instance=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category"].queryset = Category.objects.filter(user=user, is_active=True)
        if instance:
            self.fields["category"].queryset = Category.objects.filter(user=user, pk=instance.category_id)
            self.fields["category"].disabled = True
