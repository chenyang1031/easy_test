from django.db import migrations


def _rename_tables(apps, schema_editor, rename_pairs):
    connection = schema_editor.connection
    existing_tables = set(connection.introspection.table_names())
    for old_name, new_name in rename_pairs:
        if old_name in existing_tables and new_name not in existing_tables:
            schema_editor.execute(f'ALTER TABLE "{old_name}" RENAME TO "{new_name}"')
            existing_tables.remove(old_name)
            existing_tables.add(new_name)


def forward_rename(apps, schema_editor):
    rename_pairs = [
        ("test_manager_testscene", "test_scene"),
        ("test_manager_testscenenode", "test_scene_node"),
        ("test_manager_testsceneexecution", "test_scene_execution"),
    ]
    _rename_tables(apps, schema_editor, rename_pairs)


def backward_rename(apps, schema_editor):
    rename_pairs = [
        ("test_scene", "test_manager_testscene"),
        ("test_scene_node", "test_manager_testscenenode"),
        ("test_scene_execution", "test_manager_testsceneexecution"),
    ]
    _rename_tables(apps, schema_editor, rename_pairs)


class Migration(migrations.Migration):
    dependencies = [
        ("test_manager", "0033_testscene_testscenenode_testsceneexecution"),
    ]

    operations = [
        migrations.RunPython(forward_rename, backward_rename),
    ]
