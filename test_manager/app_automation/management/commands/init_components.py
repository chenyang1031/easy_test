"""
初始化 APP 组件库基础组件定义。

用法:
    python manage.py init_components

按 type 幂等写入（存在则更新 schema/默认配置，不存在则创建），
可重复执行。组件的 type 与 app_automation/runners/ui_flow_runner.py
的 action_map 一一对应，schema.properties 决定编排器配置面板的字段渲染。
"""
from django.core.management.base import BaseCommand

from test_manager.app_automation.models import AppComponent

# 选择器三件套（定位方式/目标/图片范围）在多个组件中复用
def _selector_schema(required_selector=True):
    props = {
        "selector_type": {"type": "string", "title": "定位方式"},
        "selector": {"type": "string", "title": "定位目标"},
        "image_scope": {"type": "string", "title": "图片目录"},
        "image_threshold": {"type": "number", "title": "图片匹配阈值", "min": 0.1, "max": 1, "step": 0.05},
    }
    return {
        "type": "object",
        "properties": props,
        "required": ["selector"] if required_selector else [],
    }


def _sel_defaults(selector="", selector_type="image"):
    return {
        "selector_type": selector_type,
        "selector": selector,
        "image_scope": "common",
        "image_threshold": 0.7,
    }


BASE_COMPONENTS = [
    {
        "type": "click",
        "name": "点击",
        "category": "设备操作",
        "description": "点击目标元素/坐标（支持图片、坐标、区域定位）",
        "schema": _selector_schema(),
        "default_config": _sel_defaults(),
        "sort_order": 10,
    },
    {
        "type": "double_click",
        "name": "双击",
        "category": "设备操作",
        "description": "双击目标元素/坐标",
        "schema": _selector_schema(),
        "default_config": _sel_defaults(),
        "sort_order": 20,
    },
    {
        "type": "long_press",
        "name": "长按",
        "category": "设备操作",
        "description": "长按目标元素/坐标",
        "schema": {**_selector_schema(), "properties": {
            **_selector_schema()["properties"],
            "duration": {"type": "number", "title": "长按时长(秒)", "min": 0.5, "max": 10, "step": 0.5},
        }},
        "default_config": {**_sel_defaults(), "duration": 2},
        "sort_order": 30,
    },
    {
        "type": "input",
        "name": "输入文本",
        "category": "设备操作",
        "description": "定位输入框并填充文本（先点击聚焦再输入），支持 {{变量}}",
        "schema": {"type": "object", "properties": {
            "selector_type": {"type": "string", "title": "定位方式"},
            "selector": {"type": "string", "title": "输入框定位"},
            "value": {"type": "string", "title": "输入内容"},
            "send_enter": {"type": "boolean", "title": "输入后回车"},
        }, "required": ["value"]},
        "default_config": {**_sel_defaults(), "value": "", "send_enter": False},
        "sort_order": 40,
    },
    {
        "type": "swipe",
        "name": "滑动",
        "category": "设备操作",
        "description": "从起点坐标滑动到终点坐标",
        "schema": {"type": "object", "properties": {
            "start": {"type": "string", "title": "起点坐标(x,y)"},
            "end": {"type": "string", "title": "终点坐标(x,y)"},
            "duration": {"type": "number", "title": "滑动时长(秒)", "min": 0.1, "max": 5, "step": 0.1},
        }, "required": ["start", "end"]},
        "default_config": {"start": "400,800", "end": "400,300", "duration": 0.5},
        "sort_order": 50,
    },
    {
        "type": "drag",
        "name": "拖拽",
        "category": "设备操作",
        "description": "将起点元素拖拽到终点元素",
        "schema": {"type": "object", "properties": {
            "start_selector_type": {"type": "string", "title": "起点定位方式"},
            "start_selector": {"type": "string", "title": "起点目标"},
            "end_selector_type": {"type": "string", "title": "终点定位方式"},
            "end_selector": {"type": "string", "title": "终点目标"},
            "duration": {"type": "number", "title": "拖拽时长(秒)", "min": 0.1, "max": 5, "step": 0.1},
        }, "required": ["start_selector", "end_selector"]},
        "default_config": {"start_selector_type": "image", "end_selector_type": "image", "duration": 0.5},
        "sort_order": 60,
    },
    {
        "type": "swipe_to",
        "name": "滑动查找",
        "category": "设备操作",
        "description": "朝指定方向反复滑动直到目标元素出现",
        "schema": {"type": "object", "properties": {
            "target_selector_type": {"type": "string", "title": "目标定位方式"},
            "target_selector": {"type": "string", "title": "查找目标"},
            "direction": {"type": "string", "title": "滑动方向"},
            "max_swipes": {"type": "number", "title": "最大滑动次数", "min": 1, "max": 30, "step": 1},
            "interval": {"type": "number", "title": "滑动间隔(秒)", "min": 0.1, "max": 5, "step": 0.1},
        }, "required": ["target_selector"]},
        "default_config": {"target_selector_type": "image", "direction": "up", "max_swipes": 5, "interval": 0.5},
        "sort_order": 70,
    },
    {
        "type": "wait",
        "name": "等待",
        "category": "流程控制",
        "description": "固定等待指定秒数",
        "schema": {"type": "object", "properties": {
            "timeout": {"type": "number", "title": "等待时长(秒)", "min": 0.1, "max": 300, "step": 0.5},
        }, "required": ["timeout"]},
        "default_config": {"timeout": 3},
        "sort_order": 80,
    },
    {
        "type": "screenshot",
        "name": "截图",
        "category": "流程控制",
        "description": "对当前屏幕截图并附加到报告",
        "schema": {"type": "object", "properties": {}},
        "default_config": {},
        "sort_order": 90,
    },
    {
        "type": "set_variable",
        "name": "设置变量",
        "category": "数据",
        "description": "定义一个变量供后续步骤引用（变量名即步骤名称）",
        "schema": {"type": "object", "properties": {
            "value": {"type": "string", "title": "变量值"},
            "scope": {"type": "string", "title": "作用域"},
        }, "required": ["value"]},
        "default_config": {"value": "", "scope": "local"},
        "sort_order": 100,
    },
    {
        "type": "extract_output",
        "name": "提取输出",
        "category": "数据",
        "description": "从上一提取源按路径取值写入变量（变量名即步骤名称）",
        "schema": {"type": "object", "properties": {
            "source": {"type": "string", "title": "提取源"},
            "path": {"type": "string", "title": "取值路径"},
            "scope": {"type": "string", "title": "作用域"},
        }, "required": ["source", "path"]},
        "default_config": {"source": "", "path": "", "scope": "local"},
        "sort_order": 110,
    },
    {
        "type": "assert",
        "name": "断言",
        "category": "校验",
        "description": "校验屏幕文本/元素存在性等（支持超时轮询重试）",
        "schema": {"type": "object", "properties": {
            "assert_type": {"type": "string", "title": "断言类型"},
            "selector_type": {"type": "string", "title": "定位方式"},
            "selector": {"type": "string", "title": "断言目标"},
            "expected": {"type": "string", "title": "期望值"},
            "match_mode": {"type": "string", "title": "匹配方式"},
            "timeout": {"type": "number", "title": "断言超时(秒)", "min": 0, "max": 120, "step": 1},
            "retry_interval": {"type": "number", "title": "重试间隔(秒)", "min": 0.5, "max": 10, "step": 0.5},
        }, "required": ["assert_type"]},
        "default_config": {"assert_type": "text", "selector_type": "image", "expected": "", "match_mode": "contains", "timeout": 5, "retry_interval": 1},
        "sort_order": 120,
    },
]


class Command(BaseCommand):
    help = "初始化 APP 组件库基础组件定义（按 type 幂等写入，可重复执行）"

    def handle(self, *args, **options):
        created, updated = 0, 0
        for comp in BASE_COMPONENTS:
            obj, is_created = AppComponent.objects.update_or_create(
                type=comp["type"],
                defaults={
                    "name": comp["name"],
                    "category": comp["category"],
                    "description": comp["description"],
                    "schema": comp["schema"],
                    "default_config": comp["default_config"],
                    "enabled": True,
                    "sort_order": comp["sort_order"],
                },
            )
            if is_created:
                created += 1
            else:
                updated += 1

        self.stdout.write(self.style.SUCCESS(
            f"组件库初始化完成：新增 {created} 个，更新 {updated} 个，共 {AppComponent.objects.count()} 个组件定义。"
        ))
