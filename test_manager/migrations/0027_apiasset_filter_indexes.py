from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("test_manager", "0026_apiasset_request_fields_unify"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="apiasset",
            index=models.Index(fields=["project", "group"], name="api_asset_proj_group_idx"),
        ),
        migrations.AddIndex(
            model_name="apiasset",
            index=models.Index(fields=["project", "method"], name="api_asset_proj_method_idx"),
        ),
        migrations.AddIndex(
            model_name="apiasset",
            index=models.Index(fields=["project", "status"], name="api_asset_proj_status_idx"),
        ),
        migrations.AddIndex(
            model_name="apiasset",
            index=models.Index(fields=["project", "source"], name="api_asset_proj_source_idx"),
        ),
    ]
