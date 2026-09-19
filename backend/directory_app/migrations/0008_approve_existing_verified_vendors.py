from django.db import migrations


def approve_existing_verified_vendors(apps, schema_editor):
    Vendor = apps.get_model("directory_app", "Vendor")
    Vendor.objects.filter(is_verified=True).update(approval_status="approved", is_active=True)


def reverse_approval(apps, schema_editor):
    Vendor = apps.get_model("directory_app", "Vendor")
    Vendor.objects.filter(approval_status="approved").update(approval_status="pending")


class Migration(migrations.Migration):
    dependencies = [("directory_app", "0007_phoneaccount_email_phoneaccount_email_verified_and_more")]
    operations = [migrations.RunPython(approve_existing_verified_vendors, reverse_approval)]
