from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from ninja import File, Router
from ninja.errors import HttpError
from ninja.files import UploadedFile

from apps.accounts.auth import admin

from .models import Product, ProductCategory
from .schemas import (
    CategoryAdminOut,
    CategoryIn,
    CategoryOut,
    CategoryUpdateIn,
    ProductAdminOut,
    ProductDetailOut,
    ProductIn,
    ProductListOut,
    ProductUpdateIn,
)

router = Router(tags=["shop"])


def _validate_product_fields(data: dict):
    if "title" in data and not data["title"].strip():
        raise HttpError(400, "Title cannot be blank.")
    if "product_type" in data and data["product_type"] not in Product.ProductType.values:
        raise HttpError(
            400, f"product_type must be one of: {', '.join(Product.ProductType.values)}."
        )
    if "status" in data and data["status"] not in Product.Status.values:
        raise HttpError(400, f"status must be one of: {', '.join(Product.Status.values)}.")
    if data.get("price") is not None and data["price"] < 0:
        raise HttpError(400, "price cannot be negative.")
    if data.get("compare_at_price") is not None and data["compare_at_price"] < 0:
        raise HttpError(400, "compare_at_price cannot be negative.")
    if data.get("stock_quantity") is not None and data["stock_quantity"] < 0:
        raise HttpError(400, "stock_quantity cannot be negative.")
    if "currency" in data and len(data["currency"]) != 3:
        raise HttpError(400, "currency must be a 3-letter code.")
    if data.get("category_id") is not None and not ProductCategory.objects.filter(
        pk=data["category_id"]
    ).exists():
        raise HttpError(400, "That category does not exist.")


def _admin_products():
    return Product.objects.select_related("category")


# ---------------- public (shop page) ----------------

@router.get("/categories", response=list[CategoryOut], auth=None)
def list_categories(request):
    return ProductCategory.objects.filter(is_active=True)


@router.get("/products", response=list[ProductListOut], auth=None)
def list_products(
    request,
    category: str | None = None,  # category slug
    q: str | None = None,
    featured: bool | None = None,
    product_type: str | None = None,
    sort: str = "newest",  # newest | price_asc | price_desc
):
    qs = Product.objects.select_related("category").filter(status=Product.Status.PUBLISHED)
    qs = qs.filter(Q(category__isnull=True) | Q(category__is_active=True))
    if category:
        qs = qs.filter(category__slug=category)
    if q:
        qs = qs.filter(Q(title__icontains=q) | Q(summary__icontains=q))
    if featured is not None:
        qs = qs.filter(is_featured=featured)
    if product_type:
        qs = qs.filter(product_type=product_type)
    ordering = {"newest": "-created_at", "price_asc": "price", "price_desc": "-price"}
    if sort not in ordering:
        raise HttpError(400, f"sort must be one of: {', '.join(ordering)}.")
    return qs.order_by(ordering[sort], "id")


@router.get("/products/{slug}", response=ProductDetailOut, auth=None)
def get_product(request, slug: str):
    return get_object_or_404(
        Product.objects.select_related("category"), slug=slug, status=Product.Status.PUBLISHED
    )


# ---------------- admin: categories ----------------

@router.get("/admin/categories", response=list[CategoryAdminOut], auth=admin)
def admin_list_categories(request):
    return ProductCategory.objects.annotate(product_count=Count("products"))


@router.post("/admin/categories", response={201: CategoryAdminOut}, auth=admin)
def admin_create_category(request, payload: CategoryIn):
    name = payload.name.strip()
    if not name:
        raise HttpError(400, "Name cannot be blank.")
    if ProductCategory.objects.filter(name__iexact=name).exists():
        raise HttpError(409, "A category with that name already exists.")
    category = ProductCategory.objects.create(
        name=name, order=payload.order, is_active=payload.is_active
    )
    return 201, category


@router.patch("/admin/categories/{category_id}", response=CategoryAdminOut, auth=admin)
def admin_update_category(request, category_id: int, payload: CategoryUpdateIn):
    category = get_object_or_404(ProductCategory, pk=category_id)
    data = {k: v for k, v in payload.dict(exclude_unset=True).items() if v is not None}
    if "name" in data:
        data["name"] = data["name"].strip()
        if not data["name"]:
            raise HttpError(400, "Name cannot be blank.")
        if ProductCategory.objects.filter(name__iexact=data["name"]).exclude(
            pk=category.pk
        ).exists():
            raise HttpError(409, "A category with that name already exists.")
    for field, value in data.items():
        setattr(category, field, value)
    category.save()
    return category


@router.delete("/admin/categories/{category_id}", response={200: dict}, auth=admin)
def admin_delete_category(request, category_id: int):
    category = get_object_or_404(ProductCategory, pk=category_id)
    category.delete()  # products become uncategorised (SET_NULL)
    return {"status": "deleted"}


# ---------------- admin: products ----------------

@router.get("/admin/products", response=list[ProductAdminOut], auth=admin)
def admin_list_products(
    request,
    status: str | None = None,
    category_id: int | None = None,
    q: str | None = None,
):
    qs = _admin_products()
    if status:
        qs = qs.filter(status=status)
    if category_id:
        qs = qs.filter(category_id=category_id)
    if q:
        qs = qs.filter(Q(title__icontains=q) | Q(summary__icontains=q))
    return qs


@router.post("/admin/products", response={201: ProductAdminOut}, auth=admin)
def admin_create_product(request, payload: ProductIn):
    data = payload.dict()
    _validate_product_fields(data)
    product = Product.objects.create(**data)
    return 201, _admin_products().get(pk=product.pk)


@router.get("/admin/products/{product_id}", response=ProductAdminOut, auth=admin)
def admin_get_product(request, product_id: int):
    return get_object_or_404(_admin_products(), pk=product_id)


@router.patch("/admin/products/{product_id}", response=ProductAdminOut, auth=admin)
def admin_update_product(request, product_id: int, payload: ProductUpdateIn):
    product = get_object_or_404(Product, pk=product_id)
    data = payload.dict(exclude_unset=True)
    # These may be explicitly nulled; everything else ignores null.
    nullable = {"category_id", "compare_at_price", "stock_quantity"}
    data = {k: v for k, v in data.items() if v is not None or k in nullable}
    _validate_product_fields(data)
    for field, value in data.items():
        setattr(product, field, value)
    product.save()
    return _admin_products().get(pk=product.pk)


@router.delete("/admin/products/{product_id}", response={200: dict}, auth=admin)
def admin_delete_product(request, product_id: int):
    product = get_object_or_404(Product, pk=product_id)
    if product.image:
        product.image.delete(save=False)
    product.delete()
    return {"status": "deleted"}


@router.post("/admin/products/{product_id}/image", response=ProductAdminOut, auth=admin)
def admin_upload_product_image(request, product_id: int, image: UploadedFile = File(...)):
    product = get_object_or_404(Product, pk=product_id)
    if not (image.content_type or "").startswith("image/"):
        raise HttpError(400, "The uploaded file must be an image.")
    if product.image:
        product.image.delete(save=False)
    product.image = image
    product.save(update_fields=["image", "updated_at"])
    return _admin_products().get(pk=product.pk)
