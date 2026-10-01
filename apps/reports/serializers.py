from django.utils import timezone
from rest_framework import serializers
from apps.accounts.serializers import StrictSerializer
from apps.transactions.serializers import TransactionSerializer


class PeriodSerializer(StrictSerializer):
    month = serializers.IntegerField(min_value=1, max_value=12, required=False)
    year = serializers.IntegerField(min_value=1, max_value=9998, required=False)

    def validate(self, attrs):
        today = timezone.localdate()
        return {"month": attrs.get("month", today.month), "year": attrs.get("year", today.year)}


class DailySerializer(serializers.Serializer):
    date = serializers.DateField()
    income = serializers.DecimalField(max_digits=None, decimal_places=2)
    expenses = serializers.DecimalField(max_digits=None, decimal_places=2)


class SubcategoryTotalSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    amount = serializers.DecimalField(max_digits=None, decimal_places=2)


class CategoryTotalSerializer(SubcategoryTotalSerializer):
    percentage = serializers.DecimalField(max_digits=5, decimal_places=2)
    subcategories = SubcategoryTotalSerializer(many=True)


class DashboardSerializer(serializers.Serializer):
    year = serializers.IntegerField()
    month = serializers.IntegerField()
    income = serializers.DecimalField(max_digits=None, decimal_places=2)
    expenses = serializers.DecimalField(max_digits=None, decimal_places=2)
    result = serializers.DecimalField(max_digits=None, decimal_places=2)
    count = serializers.IntegerField()
    daily = DailySerializer(many=True)
    expense_categories = CategoryTotalSerializer(many=True)
    income_categories = CategoryTotalSerializer(many=True)
    recent = serializers.SerializerMethodField()

    def get_recent(self, obj):
        return TransactionSerializer(obj["recent"], many=True, context=self.context).data
