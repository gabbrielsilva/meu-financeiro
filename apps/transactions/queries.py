from .models import Transaction
from .serializers import TransactionFilters
from django.db.models import Q
from apps.reports.periods import month_bounds


def history(request):
    filters = TransactionFilters(data=request.GET, context={"request": request})
    filters.is_valid(raise_exception=True)
    data = filters.validated_data
    rows = Transaction.objects.filter(user=request.user, deleted_at__isnull=True).select_related("category", "subcategory")
    if "month" in data:
        start, end = month_bounds(data["year"], data["month"])
        rows = rows.filter(transaction_date__gte=start, transaction_date__lt=end)
    if "q" in data:
        rows = rows.filter(Q(description__icontains=data["q"]) | Q(category__name__icontains=data["q"]) | Q(subcategory__name__icontains=data["q"]))
    for key in ("type", "category", "subcategory"):
        if key in data:
            rows = rows.filter(**{key: data[key]})
    if "date_from" in data:
        rows = rows.filter(transaction_date__gte=data["date_from"])
    if "date_to" in data:
        rows = rows.filter(transaction_date__lte=data["date_to"])
    return rows
