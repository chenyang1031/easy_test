"""
报告生成器 - 生成 UI 自动化测试报告（HTML + PDF）
"""
import logging
import os
import uuid
from datetime import datetime

logger = logging.getLogger('test_manager.ui_automation')

REPORT_DIR = os.path.join('media', 'ui_reports')


def generate_ai_report_pdf(record):
    """
    生成 AI 执行记录的 PDF 报告

    Args:
        record: UiAIExecutionRecord 实例

    Returns:
        PDF 文件 URL 路径，失败返回 None
    """
    try:
        os.makedirs(REPORT_DIR, exist_ok=True)

        filename = f"ai_report_{uuid.uuid4().hex}.html"
        filepath = os.path.join(REPORT_DIR, filename)

        html_content = _generate_ai_report_html(record)

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html_content)

        # 尝试转换为 PDF（如果安装了 weasyprint）
        try:
            from weasyprint import HTML
            pdf_filename = filename.replace('.html', '.pdf')
            pdf_filepath = os.path.join(REPORT_DIR, pdf_filename)
            HTML(filename=filepath).write_pdf(pdf_filepath)
            return f'/media/ui_reports/{pdf_filename}'
        except ImportError:
            # weasyprint 未安装，返回 HTML 报告
            logger.info("weasyprint 未安装，返回 HTML 报告")
            return f'/media/ui_reports/{filename}'
        except Exception as e:
            logger.warning(f"PDF 生成失败，返回 HTML: {e}")
            return f'/media/ui_reports/{filename}'

    except Exception as e:
        logger.exception(f"生成报告失败: {e}")
        return None


def generate_batch_report_html(batch):
    """
    生成批量执行的 HTML 报告

    Args:
        batch: UiBatchExecutionRecord 实例

    Returns:
        HTML 文件 URL 路径
    """
    try:
        os.makedirs(REPORT_DIR, exist_ok=True)

        filename = f"batch_report_{uuid.uuid4().hex}.html"
        filepath = os.path.join(REPORT_DIR, filename)

        records = batch.execution_records.select_related('test_case').all()
        passed = records.filter(status=2).count()
        failed = records.filter(status=3).count()
        total = records.count()

        rows = []
        for r in records:
            status_text = {0: '待执行', 1: '执行中', 2: '通过', 3: '失败', 4: '部分成功'}.get(r.status, '未知')
            status_class = 'pass' if r.status == 2 else 'fail' if r.status == 3 else 'other'
            rows.append(f'''
                <tr class="{status_class}">
                    <td>{r.test_case.name}</td>
                    <td>{status_text}</td>
                    <td>{r.duration:.1f}s</td>
                    <td>{r.executor}</td>
                    <td>{r.error_message[:200] if r.error_message else '-'}</td>
                </tr>
            ''')

        html = f'''<!DOCTYPE html>
<html lang="zh">
<head>
    <meta charset="UTF-8">
    <title>UI自动化测试报告 - {batch.name}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; margin: 40px; color: #333; }}
        h1 {{ color: #1a73e8; border-bottom: 2px solid #1a73e8; padding-bottom: 10px; }}
        .summary {{ display: flex; gap: 20px; margin: 20px 0; }}
        .card {{ background: #f8f9fa; padding: 20px; border-radius: 8px; min-width: 120px; text-align: center; }}
        .card .number {{ font-size: 28px; font-weight: bold; }}
        .card.pass .number {{ color: #34a853; }}
        .card.fail .number {{ color: #ea4335; }}
        .card.total .number {{ color: #1a73e8; }}
        .card.rate .number {{ color: #fbbc04; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #e0e0e0; }}
        th {{ background: #f1f3f4; font-weight: 600; }}
        tr.pass td:nth-child(2) {{ color: #34a853; font-weight: bold; }}
        tr.fail td:nth-child(2) {{ color: #ea4335; font-weight: bold; }}
        .meta {{ color: #666; font-size: 14px; }}
    </style>
</head>
<body>
    <h1>UI 自动化测试报告</h1>
    <p class="meta">批次: {batch.name} | 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>

    <div class="summary">
        <div class="card total"><div class="number">{total}</div><div>总计</div></div>
        <div class="card pass"><div class="number">{passed}</div><div>通过</div></div>
        <div class="card fail"><div class="number">{failed}</div><div>失败</div></div>
        <div class="card rate"><div class="number">{round(passed/total*100, 1) if total > 0 else 0}%</div><div>通过率</div></div>
    </div>

    <table>
        <thead>
            <tr><th>用例名称</th><th>状态</th><th>耗时</th><th>执行者</th><th>错误信息</th></tr>
        </thead>
        <tbody>
            {''.join(rows)}
        </tbody>
    </table>
</body>
</html>'''

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html)

        return f'/media/ui_reports/{filename}'

    except Exception as e:
        logger.exception(f"生成批量报告失败: {e}")
        return None


def _generate_ai_report_html(record):
    """生成 AI 执行记录的 HTML 报告内容"""
    ai_case = record.ai_case
    planned = record.planned_tasks or []
    completed = record.steps_completed or []
    screenshots = record.screenshots_sequence or []

    planned_items = ''.join(f'<li>{t}</li>' for t in planned) if isinstance(planned, list) else f'<li>{planned}</li>'
    completed_items = ''
    for s in completed:
        if isinstance(s, dict):
            completed_items += f'<li>步骤 {s.get("step", "?")}: {s.get("action", "")} - {s.get("result", "")}</li>'
        else:
            completed_items += f'<li>{s}</li>'

    screenshot_imgs = ''
    for url in screenshots:
        if isinstance(url, str):
            screenshot_imgs += f'<img src="{url}" style="max-width:100%;margin:10px 0;border:1px solid #ddd;border-radius:4px;" />'

    return f'''<!DOCTYPE html>
<html lang="zh">
<head>
    <meta charset="UTF-8">
    <title>AI 测试报告 - {ai_case.name}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; margin: 40px; color: #333; }}
        h1 {{ color: #7c3aed; border-bottom: 2px solid #7c3aed; padding-bottom: 10px; }}
        h2 {{ color: #555; margin-top: 30px; }}
        .meta {{ color: #666; font-size: 14px; }}
        .status {{ display: inline-block; padding: 4px 12px; border-radius: 12px; font-weight: bold; }}
        .status.passed {{ background: #dcfce7; color: #166534; }}
        .status.failed {{ background: #fef2f2; color: #991b1b; }}
        .stats {{ display: flex; gap: 20px; margin: 20px 0; }}
        .stat {{ background: #f8f9fa; padding: 15px; border-radius: 8px; text-align: center; }}
        .stat .value {{ font-size: 24px; font-weight: bold; color: #7c3aed; }}
        ul {{ line-height: 1.8; }}
        .logs {{ background: #1e1e1e; color: #d4d4d4; padding: 20px; border-radius: 8px; font-family: monospace; white-space: pre-wrap; max-height: 400px; overflow-y: auto; }}
    </style>
</head>
<body>
    <h1>AI 浏览器测试报告</h1>
    <p class="meta">
        用例: {ai_case.name} |
        状态: <span class="status {record.status}">{record.status}</span> |
        生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    </p>

    <div class="stats">
        <div class="stat"><div class="value">{record.duration:.1f}s</div><div>耗时</div></div>
        <div class="stat"><div class="value">{record.token_cost:.0f}</div><div>Token 消耗</div></div>
        <div class="stat"><div class="value">{len(completed)}</div><div>完成步骤</div></div>
    </div>

    <h2>任务描述</h2>
    <p>{ai_case.task_description}</p>

    <h2>计划任务</h2>
    <ul>{planned_items}</ul>

    <h2>执行步骤</h2>
    <ul>{completed_items}</ul>

    <h2>截图序列</h2>
    {screenshot_imgs if screenshot_imgs else '<p>无截图</p>'}

    <h2>执行日志</h2>
    <div class="logs">{record.logs}</div>
</body>
</html>'''
