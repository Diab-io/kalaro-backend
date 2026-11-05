from django.db import models
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

from apps.common.models import TimeStampedModel


def _unique_slug(model, base, pk):
    base = slugify(base) or "item"
    slug, n = base, 1
    while model.objects.filter(slug=slug).exclude(pk=pk).exists():
        n += 1
        slug = f"{base}-{n}"
    return slug


class ProductCategory(TimeStampedModel):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["order", "name"]
        verbose_name_plural = "product categories"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = _unique_slug(ProductCategory, self.name, self.pk)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Product(TimeStampedModel):
    class Status(models.TextChoices):
        DRAFT = "draft", _("Draft")
        PUBLISHED = "published", _("Published")
        ARCHIVED = "archived", _("Archived")

    class ProductType(models.TextChoices):
        PHYSICAL = "physical", _("Physical")
        DIGITAL = "digital", _("Digital")

    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    summary = models.CharField(max_length=300, blank=True)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to="shop_products/", blank=True, null=True)

    category = models.ForeignKey(ProductCategory, on_delete=models.SET_NULL, null=True,
                                 blank=True, related_name="products")
    product_type = models.CharField(max_length=20, choices=ProductType.choices,
                                    default=ProductType.PHYSICAL)

    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    compare_at_price = models.DecimalField(max_digits=10, decimal_places=2, null=True,
                                           blank=True)  # struck-through "was" price
    currency = models.CharField(max_length=3, default="NGN")

    # null = unlimited / not tracked (e.g. digital goods)
    stock_quantity = models.PositiveIntegerField(null=True, blank=True)

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT,
                              db_index=True)
    is_featured = models.BooleanField(default=False)

    # Card presentation: pill over the image (e.g. "Best seller") and the small
    # text next to the price (e.g. "296 pages"). Both optional, free text.
    badge = models.CharField(max_length=40, blank=True)
    detail_label = models.CharField(max_length=60, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["status", "category"])]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = _unique_slug(Product, self.title, self.pk)
        super().save(*args, **kwargs)

    @property
    def in_stock(self) -> bool:
        return self.stock_quantity is None or self.stock_quantity > 0

    def __str__(self):
        return self.title
