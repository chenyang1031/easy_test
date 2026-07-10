from django.contrib.auth.models import User
from django.test import SimpleTestCase
from rest_framework.test import APITestCase

from test_manager.models import Project, ApiProject, ApiGroup, ApiAsset, TestCase


class ApiAssetManagementAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="tester", password="pass1234")
        self.client.force_authenticate(user=self.user)

        self.platform_project = Project.objects.create(
            name="平台项目A",
            description="desc",
            created_by=self.user,
        )
        self.api_project = ApiProject.objects.create(
            platform_project=self.platform_project,
            name="API项目A",
            description="api desc",
            created_by=self.user,
        )
        self.group1 = ApiGroup.objects.create(project=self.api_project, name="分组1", sort_order=1)
        self.group2 = ApiGroup.objects.create(project=self.api_project, name="分组2", sort_order=2)

        self.asset1 = ApiAsset.objects.create(
            project=self.api_project,
            group=self.group1,
            name="查询用户",
            method="GET",
            url="/api/users",
            status=ApiAsset.STATUS_ACTIVE,
            source=ApiAsset.SOURCE_MANUAL,
            created_by=self.user,
        )
        self.asset2 = ApiAsset.objects.create(
            project=self.api_project,
            group=self.group1,
            name="新增用户",
            method="POST",
            url="/api/users/create",
            status=ApiAsset.STATUS_DRAFT,
            source=ApiAsset.SOURCE_POSTMAN,
            created_by=self.user,
        )
        self.asset3 = ApiAsset.objects.create(
            project=self.api_project,
            group=self.group2,
            name="删除用户",
            method="DELETE",
            url="/api/users/delete",
            status=ApiAsset.STATUS_ACTIVE,
            source=ApiAsset.SOURCE_APIFOX,
            created_by=self.user,
        )
        self.linked_case = TestCase.objects.create(
            name="关联用例-查询用户",
            project=self.platform_project,
            request_method="GET",
            request_url="/api/users",
            request_headers={},
            request_body={},
            request_body_format="json",
            expected_status_code=200,
            validation_rules=[],
            extract_params=[],
            created_by=self.user,
        )

    def test_list_supports_filter_and_pagination(self):
        response = self.client.get(
            "/api/v1/api-assets/",
            {
                "project": self.api_project.id,
                "group_id": self.group1.id,
                "method": "POST",
                "status": ApiAsset.STATUS_DRAFT,
                "source": ApiAsset.SOURCE_POSTMAN,
                "page": 1,
                "page_size": 10,
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["id"], self.asset2.id)
        self.assertIn("total_pages", response.data)

    def test_batch_update_status(self):
        response = self.client.post(
            "/api/v1/api-assets/batch-update-status/",
            {"ids": [self.asset1.id, self.asset2.id], "status": ApiAsset.STATUS_ACTIVE},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.asset2.refresh_from_db()
        self.assertEqual(self.asset2.status, ApiAsset.STATUS_ACTIVE)

    def test_batch_move_group(self):
        response = self.client.post(
            "/api/v1/api-assets/batch-move-group/",
            {"ids": [self.asset1.id, self.asset2.id], "group_id": self.group2.id},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.asset1.refresh_from_db()
        self.asset2.refresh_from_db()
        self.assertEqual(self.asset1.group_id, self.group2.id)
        self.assertEqual(self.asset2.group_id, self.group2.id)

    def test_batch_export(self):
        response = self.client.post(
            "/api/v1/api-assets/batch-export/",
            {"ids": [self.asset1.id, self.asset2.id], "format": "json"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 2)
        self.assertIn("paths", response.data["content"])

    def test_copy_url(self):
        response = self.client.post(f"/api/v1/api-assets/{self.asset1.id}/copy-url/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["url"], self.asset1.url)

    def test_delete_single_asset_success(self):
        response = self.client.delete(f"/api/v1/api-assets/{self.asset2.id}/")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(ApiAsset.objects.filter(id=self.asset2.id, is_deleted=False).exists())

    def test_delete_single_asset_failed_when_linked(self):
        response = self.client.delete(f"/api/v1/api-assets/{self.asset1.id}/")
        self.assertEqual(response.status_code, 400)
        self.assertIn("已被测试用例关联", response.data["detail"])
        self.assertTrue(ApiAsset.objects.filter(id=self.asset1.id).exists())

    def test_batch_delete_mixed_result(self):
        response = self.client.post(
            "/api/v1/api-assets/batch-delete/",
            {"ids": [self.asset1.id, self.asset2.id, 999999]},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["deleted_count"], 1)
        self.assertEqual(response.data["failed_count"], 2)
        self.assertTrue(ApiAsset.objects.filter(id=self.asset1.id).exists())
        self.assertFalse(ApiAsset.objects.filter(id=self.asset2.id, is_deleted=False).exists())


class ApifoxImportBodyUnitTests(SimpleTestCase):
    """Apifox 导入请求体：优先示例（api_asset_views._apifox_extract_body_format_and_payload）。"""
    def test_request_body_prefers_design_examples_over_json_schema(self):
        from test_manager.api.api_asset_views import _apifox_extract_body_format_and_payload

        schema = {"type": "object", "properties": {"a": {"type": "string"}}}
        req_body = {
            "type": "application/json",
            "parameters": [],
            "jsonSchema": schema,
            "examples": [
                {
                    "value": '{"a": "from_example"}',
                    "mediaType": "application/json",
                }
            ],
        }
        fmt, payload = _apifox_extract_body_format_and_payload(req_body)
        self.assertEqual(fmt, "json")
        self.assertEqual(payload, {"a": "from_example"})

    def test_request_body_falls_back_to_json_schema_when_no_parseable_example(self):
        from test_manager.api.api_asset_views import _apifox_extract_body_format_and_payload

        schema = {"type": "object"}
        req_body = {
            "type": "application/json",
            "jsonSchema": schema,
            "examples": [{"value": "", "mediaType": "application/json"}],
        }
        fmt, payload = _apifox_extract_body_format_and_payload(req_body)
        self.assertEqual(fmt, "json")
        self.assertEqual(payload, schema)

    def test_form_body_still_uses_parameters_not_json_examples(self):
        from test_manager.api.api_asset_views import _apifox_extract_body_format_and_payload

        req_body = {
            "type": "application/x-www-form-urlencoded",
            "parameters": [{"name": "k", "value": "v"}],
            "examples": [{"value": '{"x":1}', "mediaType": "application/json"}],
        }
        fmt, payload = _apifox_extract_body_format_and_payload(req_body)
        self.assertEqual(fmt, "form-data")
        self.assertEqual(payload, {"k": "v"})
