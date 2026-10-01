from django import forms
from django.db.models import Q
from django.utils import timezone
from apps.accounts.forms import StyledForm
from apps.categories.models import Category, MovementType, Subcategory
from .models import PaymentMethod
from apps.reports.periods import MONTHS


class TransactionForm(StyledForm):
    type = forms.ChoiceField(label="Tipo", choices=MovementType.choices, initial="DESPESA")
    amount = forms.DecimalField(label="Valor (R$)", max_digits=14, decimal_places=2, localize=True, widget=forms.TextInput(attrs={"inputmode": "decimal", "placeholder": "0,00"}))
    category = forms.ModelChoiceField(label="Categoria", queryset=Category.objects.none())
    subcategory = forms.ModelChoiceField(label="Subcategoria", queryset=Subcategory.objects.none(), help_text="Obrigatória. Escolha primeiro a categoria.")
    payment_method = forms.ChoiceField(label="Forma de movimentação", choices=PaymentMethod.choices)
    transaction_date = forms.DateField(label="Data", initial=timezone.localdate, widget=forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}))
    description = forms.CharField(label="Descrição (opcional)", required=False, max_length=500, widget=forms.Textarea(attrs={"rows": 3}))

    def __init__(self, *args, user, instance=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.order_fields(["type", "description", "amount", "transaction_date", "category", "subcategory", "payment_method"])
        self.fields["transaction_date"].widget.attrs["max"] = timezone.localdate().isoformat()
        allowed_categories = Q(is_active=True)
        allowed_subcategories = Q(is_active=True, category__is_active=True)
        if instance:
            allowed_categories |= Q(pk=instance.category_id)
            allowed_subcategories |= Q(pk=instance.subcategory_id)
        self.fields["category"].queryset = Category.objects.filter(allowed_categories, user=user)
        self.fields["subcategory"].queryset = Subcategory.objects.filter(allowed_subcategories, user=user)


class HistoryForm(StyledForm):
    q = forms.CharField(label="Busca", max_length=200, required=False, widget=forms.TextInput(attrs={"placeholder": "Buscar descrição ou categoria"}))
    month = forms.ChoiceField(label="Mês", choices=[("", "Todos os meses"), *MONTHS], required=False)
    year = forms.IntegerField(label="Ano", required=False, min_value=1, max_value=9998, widget=forms.NumberInput(attrs={"placeholder": "Ano"}))
    date_from = forms.DateField(label="De", required=False, widget=forms.DateInput(attrs={"type": "date"}))
    date_to = forms.DateField(label="Até", required=False, widget=forms.DateInput(attrs={"type": "date"}))
    type = forms.ChoiceField(label="Tipo", choices=[("", "Todos os tipos"), *MovementType.choices], required=False)
    category = forms.ModelChoiceField(label="Categoria", queryset=Category.objects.none(), required=False, empty_label="Todas as categorias")
    subcategory = forms.ModelChoiceField(label="Subcategoria", queryset=Subcategory.objects.none(), required=False, empty_label="Todas as subcategorias")

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.order_fields(["q", "type", "category", "month", "year", "date_from", "date_to", "subcategory"])
        self.fields["category"].queryset = Category.objects.filter(user=user)
        self.fields["subcategory"].queryset = Subcategory.objects.filter(user=user)
