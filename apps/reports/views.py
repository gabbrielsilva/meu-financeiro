from datetime import timedelta
from django import forms
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from rest_framework.response import Response
from rest_framework.views import APIView
from apps.accounts.forms import StyledForm
from .periods import MONTHS
from .serializers import DashboardSerializer, PeriodSerializer
from .services import chart_geometry, monthly_report


class PeriodForm(StyledForm):
    month = forms.TypedChoiceField(label="Mês", choices=MONTHS, coerce=int)
    year = forms.IntegerField(label="Ano", min_value=1, max_value=9998, widget=forms.NumberInput(attrs={"inputmode": "numeric"}))


@never_cache
@login_required
def dashboard(request):
    period = PeriodSerializer(data=request.GET.dict())
    if not period.is_valid():
        form = PeriodForm(request.GET)
        form.is_valid()
        form.add_serializer_errors(period.errors)
        return render(request, "reports/dashboard.html", {"title": "Dashboard", "period_form": form, "period_error": True}, status=400)
    selected = period.validated_data
    report = monthly_report(request.user, **selected)
    previous = report["start"] - timedelta(days=1) if report["year"] > 1 or report["month"] > 1 else None
    next_month = report["end"] if report["year"] < 9998 or report["month"] < 12 else None
    return render(request, "reports/dashboard.html", {
        "title": "Dashboard", "period_form": PeriodForm(initial=selected),
        "report": report, "chart": chart_geometry(report["daily"]),
        "previous_month": previous, "next_month": next_month,
    })


@method_decorator(never_cache, name="dispatch")
class DashboardView(APIView):
    def get(self, request):
        period = PeriodSerializer(data=request.query_params.dict())
        period.is_valid(raise_exception=True)
        report = monthly_report(request.user, **period.validated_data)
        return Response(DashboardSerializer(report, context={"request": request}).data)
