# -*- coding: utf-8 -*-
from django.contrib.auth.models import User
from django.test import TestCase

from test_manager.env_variables_compat import ENV_VAR_DESCRIPTIONS_KEY, variables_for_runtime
from test_manager.models import ApiProject, Environment, Project
from test_manager.api.apifox_environment_import import (
    apply_apifox_environment_import,
    parse_apifox_environments_from_json,
)


class ApifoxEnvironmentParseTests(TestCase):
    def test_empty_environments_array(self):
        data = {"apifoxProject": "1.0.0", "environments": [], "apiCollection": []}
        out = parse_apifox_environments_from_json(data)
        self.assertEqual(out["environments"], [])

    def test_parse_single_environment_variables(self):
        data = {
            "environments": [
                {
                    "name": "本地",
                    "baseUrl": "http://api.example.com",
                    "variables": [
                        {"name": "token", "value": "abc", "description": "访问令牌", "enabled": True},
                        {"name": "skip_me", "value": "x", "enabled": False},
                    ],
                }
            ]
        }
        out = parse_apifox_environments_from_json(data)
        self.assertEqual(len(out["environments"]), 1)
        env0 = out["environments"][0]
        self.assertEqual(env0["name"], "本地")
        self.assertEqual(env0["base_url"], "http://api.example.com")
        vars0 = env0["variables"]
        self.assertEqual(len(vars0), 2)
        self.assertTrue(vars0[0]["enabled"])
        self.assertFalse(vars0[1]["enabled"])


class ApifoxEnvironmentApplyTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="env_tester", password="pass1234")
        self.platform_project = Project.objects.create(
            name="平台项目",
            description="",
            created_by=self.user,
        )
        self.api_project = ApiProject.objects.create(
            platform_project=self.platform_project,
            name="API项目",
            description="",
            created_by=self.user,
        )

    def test_create_env_and_merge_variables(self):
        payload = {
            "environments": [
                {
                    "name": "开发",
                    "base_url": "http://dev.local",
                    "variables": [
                        {"name": "a", "value": "1", "description": "一", "enabled": True},
                        {"name": "b", "value": "2", "enabled": True},
                    ],
                }
            ]
        }
        stats = apply_apifox_environment_import(self.platform_project, payload)
        self.assertTrue(stats["applied"])
        self.assertEqual(stats["totals"]["environments_created"], 1)
        self.assertEqual(stats["totals"]["imported_total"], 2)
        self.assertEqual(stats["totals"]["new"], 2)
        self.assertEqual(stats["totals"]["overwritten"], 0)

        env = Environment.objects.get(project=self.platform_project, name="开发")
        rt = variables_for_runtime(env.variables or {})
        self.assertEqual(rt.get("a"), "1")
        self.assertEqual(rt.get("b"), "2")
        meta = (env.variables or {}).get(ENV_VAR_DESCRIPTIONS_KEY) or {}
        self.assertEqual(meta.get("a"), "一")

    def test_overwrite_and_append(self):
        env = Environment.objects.create(
            project=self.platform_project,
            name="开发",
            base_url="http://localhost",
            variables={"a": "old", "c": "3", ENV_VAR_DESCRIPTIONS_KEY: {"a": "旧说明"}},
        )
        payload = {
            "environments": [
                {
                    "name": "开发",
                    "base_url": "http://ignored.example.com",
                    "variables": [
                        {"name": "a", "value": "new", "description": "新", "enabled": True},
                        {"name": "b", "value": "2", "enabled": True},
                    ],
                }
            ]
        }
        stats = apply_apifox_environment_import(self.platform_project, payload)
        self.assertEqual(stats["totals"]["environments_reused"], 1)
        self.assertEqual(stats["totals"]["overwritten"], 1)
        self.assertEqual(stats["totals"]["new"], 1)

        env.refresh_from_db()
        rt = variables_for_runtime(env.variables or {})
        self.assertEqual(rt.get("a"), "new")
        self.assertEqual(rt.get("b"), "2")
        self.assertEqual(rt.get("c"), "3")
        meta = (env.variables or {}).get(ENV_VAR_DESCRIPTIONS_KEY) or {}
        self.assertEqual(meta.get("a"), "新")
