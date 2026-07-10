"""
前置脚本子进程执行器。

在独立子进程中执行前置脚本，避免脚本异常导致主 Django 进程退出。
通过 stdin 接收 JSON 输入，stdout 输出 JSON 结果。

支持两种模式：
- mode=test: 测试脚本，返回变量变更日志（用于环境详情页「测试脚本」）
- mode=execute: 实际执行，返回更新后的 headers/params/body 等（用于测试场景编排）

全平台统一使用 js2py + CryptoJS 执行，无系统分支。
"""
import json
import sys


def _run_test(input_data):
    """测试模式：调用 test_pre_request_script。"""
    from test_manager.pre_request_script import test_pre_request_script
    return test_pre_request_script(
        script=input_data.get("script", ""),
        env_vars=input_data.get("env_vars") or {},
        timeout_ms=input_data.get("timeout_ms", 1000),
    )


def _run_execute(input_data):
    """执行模式：调用 execute_pre_request_script（统一 js2py + CryptoJS）。"""
    from test_manager.pre_request_script import execute_pre_request_script

    new_env, new_headers, new_params, new_body, new_vars, logs = execute_pre_request_script(
        script=input_data.get("script", ""),
        env_vars=input_data.get("env_vars") or {},
        request_headers=input_data.get("request_headers") or {},
        request_params=input_data.get("request_params") or {},
        request_body=input_data.get("request_body") or {},
        variables=input_data.get("variables") or {},
        collection_variables=input_data.get("collection_variables") or {},
        request_url=input_data.get("request_url") or "",
        request_method=input_data.get("request_method") or "GET",
        content_type=input_data.get("content_type") or "application/json",
        timeout_ms=input_data.get("timeout_ms", 1000),
    )
    return {
        "success": True,
        "env": new_env,
        "headers": new_headers,
        "params": new_params,
        "body": new_body,
        "variables": new_vars,
        "logs": logs,
    }


def main():
    """从 stdin 读取 JSON，按 mode 执行，向 stdout 输出 JSON 结果。"""
    try:
        input_data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError) as e:
        sys.stderr.write(str(e))
        sys.exit(2)

    mode = input_data.get("mode", "test")

    try:
        if mode == "execute":
            result = _run_execute(input_data)
        else:
            result = _run_test(input_data)
        print(json.dumps(result, ensure_ascii=False, default=str))
        sys.exit(0)
    except Exception as e:
        if mode == "execute":
            result = {"success": False, "error": str(e)}
        else:
            result = {"success": False, "logs": [], "console": [], "error": str(e)}
        print(json.dumps(result, ensure_ascii=False, default=str))
        sys.exit(1)


if __name__ == "__main__":
    main()
