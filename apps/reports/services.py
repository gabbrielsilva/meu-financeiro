"""Monthly cash-basis reports from a single, user-scoped database snapshot."""
from calendar import monthrange
from datetime import timedelta
from decimal import Decimal

from apps.transactions.models import Transaction
from .periods import month_bounds

ZERO = Decimal("0.00")
COLORS = ["#5278f5", "#a47bea", "#ffb547", "#f77785", "#3ab6af", "#8c9aac"]


def monthly_report(user, year, month):
    start, end = month_bounds(year, month)
    # One SELECT gives totals, charts and recent rows the same snapshot, even if
    # another request edits a movement while this report is being rendered.
    rows = list(Transaction.objects.filter(
        user=user, deleted_at__isnull=True,
        transaction_date__gte=start, transaction_date__lt=end,
    ).select_related("category", "subcategory"))
    totals = {"RECEITA": ZERO, "DESPESA": ZERO}
    groups = {"RECEITA": {}, "DESPESA": {}}
    daily = [{"date": start + timedelta(days=i), "income": ZERO, "expenses": ZERO}
             for i in range(monthrange(year, month)[1])]
    for row in rows:
        totals[row.type] += row.amount
        daily[row.transaction_date.day - 1]["income" if row.type == "RECEITA" else "expenses"] += row.amount
        group = groups[row.type].setdefault(row.category_id, {
            "id": row.category_id, "name": row.category.name, "amount": ZERO, "subcategories": {},
        })
        group["amount"] += row.amount
        sub = group["subcategories"].setdefault(row.subcategory_id, {
            "id": row.subcategory_id, "name": row.subcategory.name, "amount": ZERO,
        })
        sub["amount"] += row.amount
    grouped = {}
    for kind, categories in groups.items():
        grouped[kind] = sorted(categories.values(), key=lambda item: (-item["amount"], item["id"]))
        offset = ZERO
        for index, group in enumerate(grouped[kind]):
            group["percentage"] = (group["amount"] / totals[kind] * 100).quantize(Decimal("0.01"))
            group["arc"] = f"{group['amount'] / totals[kind] * 100:.6f}"
            group["offset"] = f"{-offset:.6f}"
            offset += group["amount"] / totals[kind] * 100
            group["color"] = COLORS[index % len(COLORS)]
            group["subcategories"] = sorted(group["subcategories"].values(), key=lambda item: (-item["amount"], item["id"]))
    return {
        "year": year, "month": month, "start": start, "end": end,
        "income": totals["RECEITA"], "expenses": totals["DESPESA"],
        "result": totals["RECEITA"] - totals["DESPESA"],
        "daily": daily, "expense_categories": grouped["DESPESA"],
        "income_categories": grouped["RECEITA"], "recent": rows[:6], "count": len(rows),
    }


def chart_geometry(daily):
    """Presentation-only SVG coordinates. Financial totals stay Decimal."""
    maximum = max((max(day["income"], day["expenses"]) for day in daily), default=ZERO)
    scale = maximum or Decimal("1")
    income, expenses, markers = [], [], []
    for index, day in enumerate(daily):
        x = Decimal(64) + Decimal(index) / (len(daily) - 1) * 560
        iy = 190 - day["income"] / scale * 150
        ey = 190 - day["expenses"] / scale * 150
        income.append(f"{x:.2f},{iy:.2f}")
        expenses.append(f"{x:.2f},{ey:.2f}")
        markers.append({**day, "x": f"{x:.2f}", "iy": f"{iy:.2f}", "ey": f"{ey:.2f}"})
    return {
        "income_points": " ".join(income), "expense_points": " ".join(expenses),
        "markers": markers, "maximum": maximum, "midpoint": maximum / 2,
        "ticks": [{"label": daily[i]["date"].day, "x": markers[i]["x"]}
                  for i in (0, 6, 13, 20, len(daily) - 1)],
    }
