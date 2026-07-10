from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("test_manager", "0037_apiasset_is_deleted_testscene_is_deleted_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="testscenenode",
            name="param_type",
            field=models.CharField(
                choices=[("json", "JSON"), ("form-data", "Form Data")],
                db_comment="参数格式",
                default="json",
                max_length=20,
                verbose_name="参数格式",
            ),
        ),
        migrations.AddField(
            model_name="testscenenode",
            name="body_type",
            field=models.CharField(
                choices=[("json", "JSON"), ("form-data", "Form Data")],
                db_comment="请求体格式",
                default="json",
                max_length=20,
                verbose_name="请求体格式",
            ),
        ),
    ]
