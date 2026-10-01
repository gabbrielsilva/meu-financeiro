from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods
from rest_framework.exceptions import ValidationError
from .forms import CategoryForm, SubcategoryForm
from .models import Category, Subcategory
from .serializers import CategorySerializer, SubcategorySerializer


@never_cache
@login_required
def category_list(request):
    categories = Category.objects.filter(user=request.user).prefetch_related("subcategories")
    return render(request, "categories/list.html", {"categories": categories, "title": "Categorias"})


@never_cache
@login_required
def subcategory_list(request):
    # Keep the previous URL working while showing the integrated management area.
    return render(request, "categories/list.html", {
        "categories": Category.objects.filter(user=request.user).prefetch_related("subcategories"),
        "title": "Categorias",
    })


@never_cache
@login_required
@require_http_methods(["GET", "POST"])
def category_edit(request, pk=None):
    instance = get_object_or_404(Category, pk=pk, user=request.user) if pk else None
    initial = {key: getattr(instance, key) for key in ("name", "type", "is_active")} if instance else None
    form = CategoryForm(request.POST if request.method == "POST" else None, initial=initial, instance=instance)
    if request.method == "POST" and form.is_valid():
        serializer = CategorySerializer(instance, data=form.cleaned_data, context={"request": request})
        if serializer.is_valid():
            try:
                serializer.save(user=request.user)
            except ValidationError as exc:
                form.add_serializer_errors(exc.detail)
            else:
                messages.success(request, "Categoria salva.")
                return redirect("categories")
        else:
            form.add_serializer_errors(serializer.errors)
    return render(request, "form.html", {"form": form, "title": "Editar categoria" if instance else "Nova categoria", "back_url": "categories", "note": "Desativar impede novos lançamentos e preserva o histórico. O tipo não pode ser alterado após a criação."})


@never_cache
@login_required
@require_http_methods(["GET", "POST"])
def subcategory_edit(request, pk=None):
    instance = get_object_or_404(Subcategory, pk=pk, user=request.user) if pk else None
    initial = {key: getattr(instance, key) for key in ("name", "category", "is_active")} if instance else {}
    if not instance and request.GET.get("category"):
        initial["category"] = get_object_or_404(Category, pk=request.GET["category"] if request.GET["category"].isdigit() else 0, user=request.user, is_active=True)
    form = SubcategoryForm(request.POST if request.method == "POST" else None, user=request.user, instance=instance, initial=initial)
    if request.method == "POST" and form.is_valid():
        data = dict(form.cleaned_data, category=form.cleaned_data["category"].pk)
        serializer = SubcategorySerializer(instance, data=data, context={"request": request})
        if serializer.is_valid():
            try:
                serializer.save(user=request.user)
            except ValidationError as exc:
                form.add_serializer_errors(exc.detail)
            else:
                messages.success(request, "Subcategoria salva.")
                return redirect("subcategories")
        else:
            form.add_serializer_errors(serializer.errors)
    return render(request, "form.html", {"form": form, "title": "Editar subcategoria" if instance else "Nova subcategoria", "back_url": "subcategories", "note": "A categoria não pode ser trocada após a criação. Uma categoria inativa também impede o uso de suas subcategorias."})
