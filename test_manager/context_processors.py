"""Django 模板上下文处理器。"""


def debugtalk_functions(request):
    """将 debugtalk 函数列表注入模板上下文，供 EasyTesting 文档浮窗展示。"""
    try:
        from test_manager.httprunner_executor import get_debugtalk_functions_meta
        return {"debugtalk_functions": get_debugtalk_functions_meta()}
    except Exception:
        return {"debugtalk_functions": []}
