# -*- coding: utf-8 -*-
"""HAR 解析器单元测试（结构与 goreplay_parser.parse_gor_file 对齐）"""
import json
import os

from django.test import SimpleTestCase

from test_manager.utils.har_parser import parse_har_bytes, parse_har_file


def _fixture_path(name):
    return os.path.join(os.path.dirname(__file__), "fixtures", name)


class HarParserTests(SimpleTestCase):
    def test_parse_sample_fixture_structure(self):
        path = _fixture_path("replay_sample.har")
        with open(path, "rb") as f:
            items = parse_har_file(f)
        self.assertEqual(len(items), 4)

        r0 = items[0]
        self.assertEqual(r0["method"], "POST")
        self.assertEqual(r0["url"], "/v1/users")
        self.assertIn("api.example.com", r0["url_full"])
        self.assertEqual(r0["body"], {"name": "alice"})
        self.assertEqual(r0["request_id"], "har-0")
        self.assertIn("response", r0)
        self.assertEqual(r0["response"]["status_code"], 201)
        self.assertEqual(r0["response"]["body"], {"id": 1, "name": "alice"})

        r1 = items[1]
        self.assertEqual(r1["method"], "POST")
        self.assertEqual(r1["url"], "/v1/login?trace=1")
        self.assertEqual(r1["params"].get("trace"), "1")
        self.assertEqual(r1["body"], {"user": "bob", "pass": "secret"})
        self.assertEqual(r1["response"]["body"], {"_raw": "OK"})

        r2 = items[2]
        self.assertEqual(r2["method"], "DELETE")
        self.assertIsNone(r2["response"]["body"])

        r3 = items[3]
        self.assertEqual(r3["response"]["body"], {"a": 1})

    def test_json_request_and_empty_body(self):
        har = {
            "log": {
                "entries": [
                    {
                        "startedDateTime": "2026-01-01T00:00:00Z",
                        "request": {
                            "method": "GET",
                            "url": "https://x.test/api?q=1",
                            "headers": [],
                            "queryString": [{"name": "q", "value": "1"}],
                        },
                        "response": {"status": 200, "headers": [], "content": {}},
                    }
                ]
            }
        }
        items = parse_har_bytes(json.dumps(har).encode("utf-8"))
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["params"], {"q": "1"})
        self.assertIsNone(items[0].get("body"))
        self.assertIsNone(items[0]["response"]["body"])

    def test_utf8_bom_prefix_ok(self):
        """Fiddler 等导出可能带 UTF-8 BOM，须能解析。"""
        har = {
            "log": {
                "entries": [
                    {
                        "startedDateTime": "2026-01-01T00:00:00Z",
                        "request": {
                            "method": "GET",
                            "url": "https://x.test/a",
                            "headers": [],
                            "queryString": [],
                        },
                        "response": {"status": 200, "headers": [], "content": {}},
                    }
                ]
            }
        }
        raw = "\ufeff" + json.dumps(har)
        items = parse_har_bytes(raw.encode("utf-8"))
        self.assertEqual(len(items), 1)

    def test_invalid_json_raises(self):
        with self.assertRaises(ValueError):
            parse_har_bytes(b"not json")

    def test_not_har_raises(self):
        with self.assertRaises(ValueError):
            parse_har_bytes(json.dumps({"foo": 1}).encode("utf-8"))

    def test_connect_skipped(self):
        har = {
            "log": {
                "entries": [
                    {
                        "startedDateTime": "2026-01-01T00:00:00Z",
                        "request": {"method": "CONNECT", "url": "https://x:443"},
                        "response": {},
                    },
                    {
                        "startedDateTime": "2026-01-01T00:00:01Z",
                        "request": {
                            "method": "GET",
                            "url": "https://x.test/ok",
                            "headers": [],
                            "queryString": [],
                        },
                        "response": {"status": 200, "headers": [], "content": {}},
                    },
                ]
            }
        }
        items = parse_har_bytes(json.dumps(har).encode("utf-8"))
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["url"], "/ok")
