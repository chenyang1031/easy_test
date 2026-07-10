# Generated manually: 历史节点 api_synced_at 为空时，用节点创建时间作为「已与当时资产对齐」的基准，
# 避免列表永远不计「关联API已更新」；新创建节点由 perform_create 写入同步时间。

from django.db import migrations
from django.db.models import F


def backfill_api_synced_at(apps, schema_editor):
    TestSceneNode = apps.get_model("test_manager", "TestSceneNode")
    (
        TestSceneNode.objects.filter(api_asset_id__isnull=False, api_synced_at__isnull=True, is_deleted=False).update(
            api_synced_at=F("created_at")
        )
    )


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("test_manager", "0048_testscenenode_on_failed_default_continue"),
    ]

    operations = [
        migrations.RunPython(backfill_api_synced_at, noop_reverse),
    ]
