from django.core.cache import cache
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import Category, Locality, Region


@receiver([post_save, post_delete], sender=Category)
def invalidate_categories_cache(sender, **kwargs):
    cache.delete("categories_list_all")


@receiver([post_save, post_delete], sender=Region)
@receiver([post_save, post_delete], sender=Locality)
def invalidate_regions_cache(sender, **kwargs):
    cache.delete("regions_list_all")
