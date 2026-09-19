from django.apps import AppConfig


class DirectoryAppConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "directory_app"
    verbose_name = "Annuaire AgriLink CI"

    def ready(self):
        import directory_app.signals  # noqa
