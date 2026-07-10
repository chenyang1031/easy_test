"""
性能测试阶段2（单机增强）单元测试：配置校验、断言、CSV 占位符、阶段校验。
"""
import os
import tempfile

from django.test import TestCase

from test_manager.utils.performance_assertions import evaluate_assertion_rule, run_assertions
from test_manager.utils.performance_config import (
    PerformanceConfigError,
    validate_assertions_config,
    validate_extra_config_for_task,
    validate_stages_config,
)
from test_manager.utils.performance_csv import (
    CsvRowProvider,
    load_csv_rows,
    replace_placeholders_obj,
)


class ValidateStagesTests(TestCase):
    def test_empty_means_legacy(self):
        self.assertEqual(validate_stages_config(None, 60), [])
        self.assertEqual(validate_stages_config([], 60), [])

    def test_valid_stages(self):
        stages = [
            {"duration_sec": 30, "users": 5, "spawn_rate": 1},
            {"duration_sec": 30, "users": 10, "spawn_rate": 2},
        ]
        out = validate_stages_config(stages, 60)
        self.assertEqual(len(out), 2)
        self.assertEqual(out[0]["users"], 5)

    def test_duration_sum_mismatch(self):
        stages = [{"duration_sec": 10, "users": 1, "spawn_rate": 1}]
        with self.assertRaises(PerformanceConfigError):
            validate_stages_config(stages, 60)


class AssertionsConfigTests(TestCase):
    def test_no_assertions(self):
        self.assertEqual(validate_assertions_config(None), [])
        self.assertEqual(validate_assertions_config({}), [])

    def test_invalid_assertions_type(self):
        with self.assertRaises(PerformanceConfigError):
            validate_assertions_config({"assertions": "x"})

    def test_valid_assertions(self):
        ec = {
            "assertions": [
                {"jsonpath": "$.code", "op": "eq", "expect": 200},
                {"jsonpath": "$.data.id", "op": "not_null"},
            ]
        }
        out = validate_assertions_config(ec)
        self.assertEqual(len(out), 2)


class EvaluateAssertionsTests(TestCase):
    def test_eq_and_not_null(self):
        body = {"code": 200, "data": {"id": 1}}
        ok, _ = evaluate_assertion_rule(body, {"jsonpath": "$.code", "op": "eq", "expect": 200})
        self.assertTrue(ok)
        ok, _ = evaluate_assertion_rule(body, {"jsonpath": "$.data.id", "op": "not_null"})
        self.assertTrue(ok)

    def test_run_assertions_fail(self):
        body = {"code": 201}
        ok, msg = run_assertions(
            body,
            [{"jsonpath": "$.code", "op": "eq", "expect": 200}],
        )
        self.assertFalse(ok)


class CsvPlaceholderTests(TestCase):
    def test_nested_body(self):
        row = {"name": "alice", "token": "abc"}
        body = {"user": "{{name}}", "meta": {"t": "{{token}}"}}
        out = replace_placeholders_obj(body, row)
        self.assertEqual(out["user"], "alice")
        self.assertEqual(out["meta"]["t"], "abc")


class CsvLoadTests(TestCase):
    def test_load_utf8(self):
        content = "a,b\n1,2\n"
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False, encoding="utf-8"
        ) as f:
            f.write(content)
            path = f.name
        try:
            rows = load_csv_rows(path)
            self.assertEqual(rows[0], {"a": "1", "b": "2"})
        finally:
            os.unlink(path)


class CsvProviderTests(TestCase):
    def test_per_iteration_round_robin(self):
        rows = [{"i": "0"}, {"i": "1"}]
        p = CsvRowProvider(rows, "per_iteration")
        self.assertEqual(p.get_row_for_iteration()["i"], "0")
        self.assertEqual(p.get_row_for_iteration()["i"], "1")
        self.assertEqual(p.get_row_for_iteration()["i"], "0")

    def test_per_user_stable(self):
        rows = [{"i": "0"}, {"i": "1"}]
        p = CsvRowProvider(rows, "per_user")
        u0 = p.assign_user_index()
        u1 = p.assign_user_index()
        self.assertEqual(p.get_row_for_user_index(u0)["i"], "0")
        self.assertEqual(p.get_row_for_user_index(u1)["i"], "1")


class ExtraConfigIntegrationTests(TestCase):
    def test_full_extra_valid(self):
        ec = {
            "think_time_ms": 100,
            "csv_read_strategy": "per_iteration",
            "assertions": [{"jsonpath": "$.ok", "op": "eq", "expect": True}],
            "stages": [{"duration_sec": 60, "users": 5, "spawn_rate": 1}],
        }
        summary = validate_extra_config_for_task(ec, 60)
        self.assertEqual(summary["think_time_ms"], 100)
        self.assertEqual(len(summary["stages"]), 1)
