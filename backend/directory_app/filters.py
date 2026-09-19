import django_filters

from .models import Vendor


class VendorFilter(django_filters.FilterSet):
    region = django_filters.NumberFilter(field_name="region_id")
    locality = django_filters.NumberFilter(field_name="locality_id")
    category = django_filters.NumberFilter(field_name="stock_items__product__category_id")
    category_slug = django_filters.CharFilter(field_name="stock_items__product__category__slug")
    product = django_filters.NumberFilter(field_name="stock_items__product_id")
    product_slug = django_filters.CharFilter(field_name="stock_items__product__slug")
    vendor_type = django_filters.CharFilter(field_name="vendor_type")
    available = django_filters.BooleanFilter(method="filter_available")

    class Meta:
        model = Vendor
        fields = [
            "region",
            "locality",
            "category",
            "category_slug",
            "product",
            "product_slug",
            "vendor_type",
            "available",
        ]

    def filter_available(self, queryset, name, value):
        if value is True:
            return queryset.filter(
                stock_items__is_available=True,
                stock_items__quantity_available__gt=0,
            )
        if value is False:
            return queryset.exclude(
                stock_items__is_available=True,
                stock_items__quantity_available__gt=0,
            )
        return queryset
