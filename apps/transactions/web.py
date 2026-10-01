from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods
from rest_framework.exceptions import ValidationError
from apps.categories.models import Category, Subcategory
from .forms import HistoryForm, TransactionForm
from .models import Transaction
from .queries import history
from .serializers import TransactionSerializer
from .services import soft_delete


@never_cache
@login_required
def transaction_list(request):
    form = HistoryForm(request.GET or None, user=request.user)
    # Empty controls are omitted before sharing the API filter validation.
    request.GET = request.GET.copy()
    for key in list(request.GET):
        if request.GET[key] == "":
            del request.GET[key]
    try:
        rows = history(request)
    except ValidationError as exc:
        form.is_valid()
        form.add_serializer_errors(exc.detail)
        rows = Transaction.objects.none()
    page = Paginator(rows, 20).get_page(request.GET.get("page", 1))
    params = request.GET.copy()
    params.pop("page", None)
    return render(request, "transactions/history.html", {"title": "Movimentações", "form": form, "page_obj": page, "filter_query": params.urlencode()})


@never_cache
@login_required
@require_http_methods(["GET", "POST"])
def transaction_edit(request, pk=None):
    instance = get_object_or_404(Transaction, pk=pk, user=request.user, deleted_at__isnull=True) if pk else None
    keys = ("type", "amount", "category", "subcategory", "payment_method", "description", "transaction_date")
    initial = {key: getattr(instance, key) for key in keys} if instance else None
    form = TransactionForm(request.POST if request.method == "POST" else None, user=request.user, instance=instance, initial=initial)
    if request.method == "POST" and form.is_valid():
        data = dict(form.cleaned_data)
        data.update(category=data["category"].pk, subcategory=data["subcategory"].pk)
        serializer = TransactionSerializer(instance, data=data, context={"request": request})
        if serializer.is_valid():
            try:
                serializer.save(user=request.user)
            except ValidationError as exc:
                form.add_serializer_errors(exc.detail)
            else:
                messages.success(request, "Movimentação salva.")
                return redirect("transactions")
        else:
            form.add_serializer_errors(serializer.errors)
    categories = list(form.fields["category"].queryset.values("id", "name", "type", "is_active"))
    subcategories = list(form.fields["subcategory"].queryset.values("id", "name", "category_id", "is_active"))
    return render(request, "transactions/form.html", {
        "title": "Editar movimentação" if instance else "Nova movimentação", "form": form,
        "categories_data": categories, "subcategories_data": subcategories,
        "preserved_category": instance.category_id if instance else None,
        "preserved_subcategory": instance.subcategory_id if instance else None,
    })


@never_cache
@login_required
@require_http_methods(["GET", "POST"])
def transaction_delete(request, pk):
    movement = get_object_or_404(Transaction, pk=pk, user=request.user, deleted_at__isnull=True)
    if request.method == "POST":
        soft_delete(movement)
        messages.success(request, "Movimentação excluída do histórico.")
        return redirect("transactions")
    return render(request, "transactions/delete.html", {"title": "Excluir movimentação", "movement": movement})
