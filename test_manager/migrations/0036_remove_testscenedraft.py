from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("test_manager", "0035_testscenedraft"),
    ]

    operations = [
        migrations.DeleteModel(
            name="TestSceneDraft",
        ),
    ]
