from datetime import datetime
from decimal import Decimal

from ninja import Schema

# ---- inputs ----


class CategoryIn(Schema):
    name: str
    order: int = 0
    is_active: bool = True


class CategoryUpdateIn(Schema):
    name: str | None = None
    order: int | None = None
    is_active: bool | None = None


class ProductIn(Schema):
    title: str
    summary: str = ""
    description: str = ""
    category_id: int | None = None
    product_type: str = "physical"
    price: Decimal = Decimal("0")
    compare_at_price: Decimal | None = None
    currency: str = "NGN"
    stock_quantity: int | None = None
    status: str = "draft"
    is_featured: bool = False
    badge: str = ""
    detail_label: str = ""


class ProductUpdateIn(Schema):
    title: str | None = None
    summary: str | None = None
    description: str | None = None
    category_id: int | None = None  # null explicitly = uncategorised
    product_type: str | None = None
    price: Decimal | None = None
    compare_at_price: Decimal | None = None  # null explicitly = clear
    currency: str | None = None
    stock_quantity: int | None = None  # null explicitly = unlimited
    status: str | None = None
    is_featured: bool | None = None
    badge: str | None = None
    detail_label: str | None = None


# ---- outputs ----


class CategoryOut(Schema):
    id: int
    name: str
    slug: str
    order: int
    is_active: bool


class CategoryAdminOut(CategoryOut):
    product_count: int = 0

    @staticmethod
    def resolve_product_count(obj):
        count = getattr(obj, "product_count", None)  # annotated on the list endpoint
        return count if count is not None else obj.products.count()


class ProductListOut(Schema):
    id: int
    title: str
    slug: str
    summary: str
    image: str | None = None
    category_id: int | None = None
    category_name: str | None = None
    product_type: str
    price: float  # numeric in JSON, matching the course endpoints
    compare_at_price: float | None = None
    currency: str
    in_stock: bool
    is_featured: bool
    badge: str
    detail_label: str

    @staticmethod
    def resolve_image(obj):
        return obj.image.url if obj.image else None

    @staticmethod
    def resolve_category_name(obj):
        return obj.category.name if obj.category_id else None


class ProductDetailOut(ProductListOut):
    description: str


class ProductAdminOut(ProductDetailOut):
    status: str
    stock_quantity: int | None = None
    created_at: datetime
    updated_at: datetime
