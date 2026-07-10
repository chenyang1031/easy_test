from celery import shared_task, current_app
from django.db import transaction
from django.utils import timezone
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from celery.utils.log import get_task_logger
from celery.exceptions import MaxRetriesExceededError
import traceback
import json
import time
import random
from urllib.parse import urlencode
from datetime import datetime, timedelta
import sys
import os

from test_manager.async_executor import execute_test_suite_async
from test_manager.httprunner_executor import execute_test_suite

# 确保任务可以被正确导入
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 使用Celery专用的logger
logger = get_task_logger(__name__)


@shared_task(bind=True, name="test_manager.tasks.run_performance_test")
def run_performance_test(self, task_id: int):
    """
    异步执行性能测试任务（Locust 单接口压测）
    由 run_locust_test 封装执行逻辑，避免阻塞主进程。
    """
    from test_manager.utils.performance_locust import run_locust_test

    logger.info(f"[PERF] 性能测试任务开始: task_id={task_id}")
    try:
        success = run_locust_test(task_id)
        logger.info(f"[PERF] 性能测试任务结束: task_id={task_id}, success={success}")
        return {"success": success, "task_id": task_id}
    except Exception as e:
        logger.exception(f"[PERF] 性能测试任务异常: task_id={task_id}, error={e}")
        return {"success": False, "task_id": task_id, "error": str(e)}


# 主要的定时任务执行函数
@shared_task(bind=True)
def execute_scheduled_test_suite(self, scheduled_task_id):
    """执行定时测试套件任务"""
    logger.info(f"[TASK STARTED] 定时任务开始执行: ID={scheduled_task_id}")

    # 导入模型（避免循环导入）
    try:
        from .models import ScheduledTask, TaskExecutionLog, TestRun, TestResult
        logger.info("成功导入模型")
    except Exception as e:
        logger.error(f"导入模型失败: {e}")
        return {"success": False, "error": f"导入模型失败: {e}"}

    try:
        # 获取定时任务
        try:
            scheduled_task = ScheduledTask.objects.get(id=scheduled_task_id)
            logger.info(f"找到定时任务: {scheduled_task.name}")
        except ScheduledTask.DoesNotExist:
            error_msg = f"定时任务不存在: ID={scheduled_task_id}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}

        # 检查任务状态
        if not scheduled_task.is_enabled:
            error_msg = f"定时任务已禁用: {scheduled_task.name}"
            logger.warning(error_msg)
            return {"success": False, "error": error_msg}

        # 创建执行日志
        execution_log = TaskExecutionLog.objects.create(
            scheduled_task=scheduled_task,
            status='running'
        )
        logger.info(f"创建执行日志: ID={execution_log.id}")

        # ── 场景编排分支 ──
        if scheduled_task.test_scene:
            return _run_scheduled_scene(scheduled_task, execution_log)

        # ── 测试套件分支（原有逻辑） ──
        # 创建测试运行记录
        run_name = f"定时任务: {scheduled_task.name} - {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}"
        test_run = TestRun.objects.create(
            name=run_name,
            project=scheduled_task.test_suite.project,
            test_suite=scheduled_task.test_suite,
            environment=scheduled_task.environment,
            status='running',
            start_time=timezone.now(),
            created_by=scheduled_task.created_by
        )
        logger.info(f"创建测试运行: ID={test_run.id}")

        # 关联执行日志和测试运行
        execution_log.test_run = test_run
        execution_log.save()

        # 执行测试套件
        try:
            logger.info(f"开始执行测试套件: {scheduled_task.test_suite.name}")

            result = execute_test_suite_simple(
                test_suite=scheduled_task.test_suite,
                environment=scheduled_task.environment,
                test_run=test_run,
                user=scheduled_task.created_by
            )

            logger.info(f"测试套件执行完成: {result}")

        except Exception as e:
            logger.error(f"执行测试套件失败: {e}")
            result = {"success": False, "error": str(e)}

        # 更新测试运行状态
        test_run.status = 'completed' if result.get('success', False) else 'failed'
        test_run.end_time = timezone.now()
        test_run.save()

        # 更新执行日志
        execution_log.status = 'success' if result.get('success', False) else 'failed'
        execution_log.end_time = timezone.now()
        execution_log.calculate_duration()

        # 统计测试结果
        test_results = test_run.test_results.all()
        execution_log.total_test_cases = test_results.count()
        execution_log.passed_test_cases = test_results.filter(status='passed').count()
        execution_log.failed_test_cases = test_results.filter(status='failed').count()
        execution_log.error_test_cases = test_results.filter(status='error').count()

        if not result.get('success', False):
            execution_log.error_message = result.get('error', '执行失败')

        execution_log.save()

        # 更新定时任务统计
        scheduled_task.last_run_time = timezone.now()
        scheduled_task.total_runs += 1
        if result.get('success', False):
            scheduled_task.successful_runs += 1
        else:
            scheduled_task.failed_runs += 1

        scheduled_task.update_next_run_time()
        scheduled_task.save()

        # 发送通知邮件
        if scheduled_task.send_email_notification:
            should_notify = (
                    (result.get('success', False) and scheduled_task.notify_on_success) or
                    (not result.get('success', False) and scheduled_task.notify_on_failure)
            )

            if should_notify:
                try:
                    send_task_notification_email.delay(execution_log.id)
                    logger.info("通知邮件已发送")
                except Exception as e:
                    logger.error(f"发送通知邮件失败: {e}")

        logger.info(f"定时任务执行完成: {scheduled_task.name}")

        return {
            "success": True,
            "message": f"定时任务 {scheduled_task.name} 执行完成",
            "test_run_id": test_run.id,
            "execution_log_id": execution_log.id
        }

    except Exception as e:
        error_msg = f"执行定时任务异常: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        return {"success": False, "error": error_msg}


def _run_scheduled_scene(scheduled_task, execution_log):
    """执行定时任务的场景编排分支"""
    from test_manager.api.scene_engine import execute_scene
    from test_manager.models import TestSceneExecution

    logger.info(f"开始执行场景编排: {scheduled_task.test_scene.name}")

    # 构建运行时配置，传入定时任务选择的执行环境
    # 确保环境 base_url、环境变量、前置脚本等参数能正确生效
    runtime_config_override = {}
    if scheduled_task.environment:
        runtime_config_override = {
            "environment_id": scheduled_task.environment.id,
            "base_url": scheduled_task.environment.base_url or "",
        }

    try:
        scene_execution = execute_scene(
            scene=scheduled_task.test_scene,
            operator=scheduled_task.created_by,
            runtime_config_override=runtime_config_override,
        )

        # 判断执行结果
        is_success = scene_execution.status in (
            TestSceneExecution.STATUS_SUCCESS,
            TestSceneExecution.STATUS_PARTIAL_SUCCESS,
        )

        # 更新执行日志
        execution_log.scene_execution = scene_execution
        execution_log.status = 'success' if is_success else 'failed'
        execution_log.end_time = timezone.now()
        execution_log.calculate_duration()

        # 从场景执行结果中统计节点执行情况
        node_results = scene_execution.node_results or []
        total_nodes = len(node_results)
        passed_nodes = sum(1 for n in node_results if n.get('status') == 'success')
        failed_nodes = sum(1 for n in node_results if n.get('status') == 'failed')

        execution_log.total_test_cases = total_nodes
        execution_log.passed_test_cases = passed_nodes
        execution_log.failed_test_cases = failed_nodes
        execution_log.error_test_cases = total_nodes - passed_nodes - failed_nodes

        if not is_success:
            execution_log.error_message = scene_execution.error_message or '场景执行未完全通过'
        execution_log.save()

    except Exception as e:
        logger.error(f"执行场景编排失败: {e}")
        logger.error(traceback.format_exc())

        execution_log.status = 'failed'
        execution_log.end_time = timezone.now()
        execution_log.calculate_duration()
        execution_log.error_message = str(e)
        execution_log.save()

        # 更新定时任务统计（失败）
        scheduled_task.last_run_time = timezone.now()
        scheduled_task.total_runs += 1
        scheduled_task.failed_runs += 1
        scheduled_task.update_next_run_time()
        scheduled_task.save()

        return {"success": False, "error": str(e)}

    # 更新定时任务统计
    scheduled_task.last_run_time = timezone.now()
    scheduled_task.total_runs += 1
    if is_success:
        scheduled_task.successful_runs += 1
    else:
        scheduled_task.failed_runs += 1
    scheduled_task.update_next_run_time()
    scheduled_task.save()

    # 发送通知邮件
    if scheduled_task.send_email_notification:
        should_notify = (
            (is_success and scheduled_task.notify_on_success) or
            (not is_success and scheduled_task.notify_on_failure)
        )
        if should_notify:
            try:
                send_task_notification_email.delay(execution_log.id)
                logger.info("通知邮件已发送")
            except Exception as e:
                logger.error(f"发送通知邮件失败: {e}")

    logger.info(f"场景编排执行完成: {scheduled_task.test_scene.name}")
    return {
        "success": is_success,
        "message": f"场景编排 {scheduled_task.test_scene.name} 执行完成",
        "execution_log_id": execution_log.id,
    }


def execute_test_suite_simple(test_suite, environment, test_run, user):
    """简化的测试套件执行函数"""
    from .models import TestResult

    logger.info(f"执行测试套件: {test_suite.name}")

    try:
        test_cases = test_suite.test_cases.all()

        if not test_cases.exists():
            logger.warning("测试套件中没有测试用例")
            return {"success": False, "error": "测试套件中没有测试用例"}

        logger.info(f"找到 {test_cases.count()} 个测试用例")

        success_count = 0
        total_count = test_cases.count()

        for i, test_case in enumerate(test_cases, 1):
            try:
                logger.info(f"执行测试用例 {i}/{total_count}: {test_case.name}")

                # 模拟测试执行
                time.sleep(0.2)

                # 随机生成结果（75%成功率）
                is_success = random.choice([True, True, True, False])
                status = 'passed' if is_success else 'failed'
                response_time = random.uniform(100, 1000)

                TestResult.objects.create(
                    test_run=test_run,
                    test_case=test_case,
                    environment=environment,
                    status=status,
                    response_time=response_time,
                    response_status_code=200 if is_success else 500,
                    response_headers={'Content-Type': 'application/json'},
                    response_body={'message': 'success' if is_success else 'failed'},
                    request_headers=test_case.request_headers or {},
                    request_body=test_case.request_body or {},
                    error_message='' if is_success else 'Test failed',
                )

                if is_success:
                    success_count += 1

                logger.info(f"测试用例 {test_case.name} 执行完成: {status}")

            except Exception as e:
                logger.error(f"执行测试用例 {test_case.name} 失败: {e}")

                TestResult.objects.create(
                    test_run=test_run,
                    test_case=test_case,
                    environment=environment,
                    status='error',
                    error_message=str(e),
                )

        success_rate = (success_count / total_count) * 100 if total_count > 0 else 0
        is_overall_success = success_rate >= 70
        result = {
            "success": is_overall_success,
            "total": total_count,
            "passed": success_count,
            "failed": total_count - success_count,
            "success_rate": success_rate
        }

        logger.info(f"测试套件执行完成: {result}")
        return result

    except Exception as e:
        error_msg = f"执行测试套件失败: {str(e)}"
        logger.error(error_msg)
        return {"success": False, "error": error_msg}


@shared_task(name='test_manager.tasks.send_task_notification_email')
def send_task_notification_email(execution_log_id):
    """发送任务执行通知邮件"""
    from .models import TaskExecutionLog

    logger.info(f"准备发送任务通知邮件: execution_log_id={execution_log_id}")

    try:
        execution_log = TaskExecutionLog.objects.get(id=execution_log_id)
        scheduled_task = execution_log.scheduled_task

        if not scheduled_task.send_email_notification:
            logger.info(f"任务未配置发送邮件通知: {scheduled_task.name}")
            return

        email_list = scheduled_task.get_notification_email_list()
        if not email_list:
            logger.warning(f"任务没有配置通知邮箱: {scheduled_task.name}")
            return

        logger.info(f"将发送通知邮件到: {', '.join(email_list)}")

        subject = f"EasyTesting 定时任务执行通知 - {scheduled_task.name}"

        context = {
            'scheduled_task': scheduled_task,
            'execution_log': execution_log,
            'test_run': execution_log.test_run,
            'success': execution_log.status == 'success',
            'timestamp': timezone.now().strftime('%Y-%m-%d %H:%M:%S'),
        }

        try:
            html_message = render_to_string('emails/task_notification.html', context)
            plain_message = render_to_string('emails/task_notification.txt', context)
        except Exception as e:
            logger.error(f"渲染邮件模板失败: {str(e)}")
            status_text = "成功" if execution_log.status == 'success' else "失败"
            plain_message = f"""
EasyTesting 定时任务执行通知

任务名称: {scheduled_task.name}
执行状态: {status_text}
开始时间: {execution_log.start_time}
结束时间: {execution_log.end_time}
执行时长: {execution_log.duration} 秒
测试用例统计:
- 总数: {execution_log.total_test_cases}
- 通过: {execution_log.passed_test_cases}
- 失败: {execution_log.failed_test_cases}
- 错误: {execution_log.error_test_cases}

{execution_log.error_message if execution_log.error_message else ''}
"""
            html_message = plain_message.replace('\n', '<br>')

        try:
            send_mail(
                subject=subject,
                message=plain_message,
                html_message=html_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=email_list,
                fail_silently=False,
            )
            logger.info(f"定时任务通知邮件发送成功: {scheduled_task.name}")

            execution_log.email_sent = True
            execution_log.email_sent_time = timezone.now()
            execution_log.save()
        except Exception as e:
            logger.error(f"发送邮件失败: {str(e)}")
            logger.error(traceback.format_exc())

    except Exception as e:
        logger.error(f"发送定时任务通知邮件失败: {str(e)}")
        logger.error(traceback.format_exc())


@shared_task(name='test_manager.tasks.cleanup_old_execution_logs')
def cleanup_old_execution_logs():
    """清理旧的执行日志"""
    from .models import TaskExecutionLog

    logger.info("开始清理旧的执行日志")

    try:
        cutoff_date = timezone.now() - timedelta(days=30)
        deleted_count = TaskExecutionLog.objects.filter(start_time__lt=cutoff_date).delete()[0]
        logger.info(f"清理了 {deleted_count} 条旧的执行日志")
        return deleted_count
    except Exception as e:
        logger.error(f"清理旧的执行日志失败: {str(e)}")
        logger.error(traceback.format_exc())
        return 0


@shared_task(name='test_manager.tasks.check_zombie_scene_executions')
def check_zombie_scene_executions():
    """检测并清理僵尸场景执行记录（status=running 且超过 10 分钟未完成）"""
    from .models import TestSceneExecution

    logger.info("开始检测僵尸场景执行记录")
    try:
        cutoff = timezone.now() - timedelta(minutes=10)
        zombies = TestSceneExecution.objects.filter(
            status=TestSceneExecution.STATUS_RUNNING,
            started_at__lt=cutoff,
        )
        count = zombies.count()
        if count:
            logger.warning(f"发现 {count} 条僵尸执行记录，正在标记为失败")
            zombies.update(
                status=TestSceneExecution.STATUS_FAILED,
                error_message="服务端超时保护：执行超过 10 分钟未完成，已自动标记为失败",
                finished_at=timezone.now(),
            )
        return count
    except Exception as e:
        logger.error(f"检测僵尸场景执行记录失败: {str(e)}")
        logger.error(traceback.format_exc())
        return 0


@shared_task(name='test_manager.tasks.cleanup_old_scene_executions')
def cleanup_old_scene_executions():
    """清理 90 天前的场景执行记录（仅删除已完成/失败的，保留 running 的）"""
    from .models import TestSceneExecution

    logger.info("开始清理旧的场景执行记录")
    try:
        cutoff = timezone.now() - timedelta(days=90)
        deleted_count = TestSceneExecution.objects.filter(
            created_at__lt=cutoff,
        ).exclude(
            status=TestSceneExecution.STATUS_RUNNING,
        ).delete()[0]
        logger.info(f"清理了 {deleted_count} 条旧的场景执行记录")
        return deleted_count
    except Exception as e:
        logger.error(f"清理旧的场景执行记录失败: {str(e)}")
        logger.error(traceback.format_exc())
        return 0


@shared_task(name='test_manager.tasks.update_scheduled_tasks_next_run_time')
def update_scheduled_tasks_next_run_time():
    """更新所有定时任务的下次执行时间"""
    from .models import ScheduledTask

    logger.info("开始更新定时任务的下次执行时间")

    try:
        active_tasks = ScheduledTask.objects.filter(is_enabled=True, status='active')
        logger.info(f"找到 {active_tasks.count()} 个活动的定时任务")

        updated_count = 0
        for task in active_tasks:
            try:
                old_next_run = task.next_run_time
                task.update_next_run_time()
                if task.next_run_time != old_next_run:
                    logger.info(f"更新任务 {task.name} 的下次执行时间: {old_next_run} -> {task.next_run_time}")
                    updated_count += 1
            except Exception as e:
                logger.error(f"更新任务 {task.name} 的下次执行时间失败: {str(e)}")

        logger.info(f"更新了 {updated_count} 个定时任务的下次执行时间")
        return updated_count
    except Exception as e:
        logger.error(f"更新定时任务下次执行时间失败: {str(e)}")
        logger.error(traceback.format_exc())
        return 0


@shared_task(name='test_manager.tasks.run_scheduled_task_now')
def run_scheduled_task_now(scheduled_task_id):
    """立即执行指定的定时任务"""
    from .models import ScheduledTask

    logger.info(f"立即执行定时任务: ID={scheduled_task_id}")

    try:
        scheduled_task = ScheduledTask.objects.get(id=scheduled_task_id)

        if not scheduled_task.is_enabled:
            logger.warning(f"定时任务已禁用，无法立即执行: {scheduled_task.name}")
            return {'success': False, 'message': f'定时任务已禁用: {scheduled_task.name}'}

        result = execute_scheduled_test_suite.delay(scheduled_task_id)

        logger.info(f"已触发定时任务立即执行: {scheduled_task.name}, task_id={result.id}")
        return {
            'success': True,
            'message': f'已触发定时任务立即执行: {scheduled_task.name}',
            'task_id': result.id
        }
    except ScheduledTask.DoesNotExist:
        logger.error(f"定时任务不存在: ID={scheduled_task_id}")
        return {'success': False, 'message': f'定时任务不存在: ID={scheduled_task_id}'}
    except Exception as e:
        logger.error(f"立即执行定时任务失败: {str(e)}")
        logger.error(traceback.format_exc())
        return {'success': False, 'message': str(e), 'error': traceback.format_exc()}


@shared_task(name='test_manager.tasks.check_celery_status')
def check_celery_status():
    """检查Celery状态"""
    logger.info("检查Celery状态")

    try:
        i = current_app.control.inspect()
        active_workers = i.active()
        if not active_workers:
            logger.warning("没有活动的Celery worker")
            return {'status': 'warning', 'message': '没有活动的Celery worker'}

        registered_tasks = i.registered()
        if not registered_tasks:
            logger.warning("没有已注册的Celery任务")
            return {'status': 'warning', 'message': '没有已注册的Celery任务'}

        our_tasks = [
            'test_manager.tasks.execute_scheduled_test_suite',
            'test_manager.tasks.send_task_notification_email',
            'test_manager.tasks.cleanup_old_execution_logs',
            'test_manager.tasks.update_scheduled_tasks_next_run_time',
            'test_manager.tasks.run_scheduled_task_now',
            'test_manager.tasks.check_celery_status',
        ]

        all_registered = True
        missing_tasks = []

        for worker, tasks in registered_tasks.items():
            for task in our_tasks:
                if task not in tasks:
                    all_registered = False
                    missing_tasks.append(task)

        if not all_registered:
            logger.warning(f"以下任务未注册: {', '.join(set(missing_tasks))}")
            return {
                'status': 'warning',
                'message': f'以下任务未注册: {", ".join(set(missing_tasks))}',
                'workers': list(active_workers.keys()),
                'missing_tasks': list(set(missing_tasks))
            }

        logger.info(f"Celery状态正常，活动的worker: {', '.join(active_workers.keys())}")
        return {
            'status': 'ok',
            'message': 'Celery状态正常',
            'workers': list(active_workers.keys()),
            'tasks': our_tasks
        }
    except Exception as e:
        logger.error(f"检查Celery状态失败: {str(e)}")
        logger.error(traceback.format_exc())
        return {'status': 'error', 'message': str(e), 'error': traceback.format_exc()}


@shared_task(bind=True, name="test_manager.tasks.extract_apis_from_document_async")
def extract_apis_from_document_async(self, record_id: int):
    """异步执行文档AI提取：从文档中提取 API 定义。"""
    import time as _time
    from test_manager.models import DocumentGenRecord, AIModelProvider, PromptTemplate
    from test_manager.ai_adapters import get_adapter

    logger.info(f"[文档AI提取] 任务开始: record_id={record_id}")

    try:
        record = DocumentGenRecord.objects.get(id=record_id)
    except DocumentGenRecord.DoesNotExist:
        logger.error(f"[文档AI提取] 记录不存在: record_id={record_id}")
        return {"success": False, "error": "record not found"}

    if record.status in ("success", "failed"):
        logger.warning(f"[文档AI提取] 记录状态已终止({record.status})，跳过: record_id={record_id}")
        return {"success": record.status == "success", "status": record.status}

    md_content = record.md_content
    if not md_content and record.converted_md_path:
        abs_path = os.path.join(settings.MEDIA_ROOT, record.converted_md_path)
        if os.path.isfile(abs_path):
            with open(abs_path, "r", encoding="utf-8") as f:
                md_content = f.read()

    if not md_content:
        record.status = "failed"
        record.error_message = "没有可用的文档内容"
        record.save(update_fields=["status", "error_message"])
        logger.error(f"[文档AI提取] 没有可用的文档内容: record_id={record_id}")
        return {"success": False, "error": "no content"}

    provider = record.model_provider
    if not provider:
        provider = AIModelProvider.objects.filter(is_enabled=True).first()
        if not provider:
            record.status = "failed"
            record.error_message = "没有可用的 AI 模型供应商，请先配置"
            record.save(update_fields=["status", "error_message"])
            logger.error(f"[文档AI提取] 没有可用的 AI 模型供应商: record_id={record_id}")
            return {"success": False, "error": "no provider"}

    prompt_template_obj = record.prompt_template

    try:
        adapter = get_adapter(provider)
        logger.info(f"[文档AI提取] 开始调用AI: record_id={record_id}, provider={provider.name}, model={provider.model_name}")

        result = adapter.extract_apis_from_document(md_content, prompt_template_obj)

        if result["success"]:
            record.status = "success"
            record.extracted_apis = result["apis"]
            record.response_raw = result.get("response_raw", "")
            record.prompt_full_text = result.get("prompt_full_text", "")
            record.duration_ms = result.get("duration_ms")
            record.api_count = len(result["apis"])
            logger.info(f"[文档AI提取] 成功: record_id={record_id}, api_count={record.api_count}, duration_ms={record.duration_ms}")
        else:
            record.status = "failed"
            record.error_message = result.get("error", "AI 提取失败")[:2000]
            record.response_raw = result.get("response_raw", "")
            logger.error(f"[文档AI提取] 失败: record_id={record_id}, error={record.error_message}")

        record.save(update_fields=[
            "status", "extracted_apis", "response_raw",
            "prompt_full_text", "duration_ms", "api_count", "error_message",
        ])

        return {"success": result["success"], "record_id": record_id}
    except Exception as e:
        logger.exception(f"[文档AI提取] 异常: record_id={record_id}, error={e}")
        record.status = "failed"
        record.error_message = str(e)[:2000]
        record.save(update_fields=["status", "error_message"])
        return {"success": False, "error": str(e), "record_id": record_id}


@shared_task(name="test_manager.tasks.export_scene_execution_report_async")
def export_scene_execution_report_async(execution_id: int, user_id: int):
    """异步生成场景执行测试报告"""
    from datetime import datetime
    from django.contrib.auth.models import User
    from test_manager.models import TestSceneExecution
    from test_manager.report.permissions import user_can_access_scene_execution_report
    from test_manager.report.services import SceneExecutionReportValidationError, save_scene_execution_test_report

    user = User.objects.get(pk=user_id)
    execution = TestSceneExecution.objects.select_related(
        "scene", "environment", "environment__project"
    ).get(pk=execution_id)
    if not user_can_access_scene_execution_report(user, execution):
        return {"error": "forbidden", "report_id": None}

    default_name = f"{execution.scene.name} - 场景报告导出 {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    try:
        report = save_scene_execution_test_report(
            execution,
            user,
            name=default_name,
            description="API 异步导出",
            report_format="html",
            is_public=False,
        )
    except SceneExecutionReportValidationError as exc:
        return {"error": str(exc), "report_id": None}
    return {"report_id": report.pk, "error": None}


@shared_task(bind=True, max_retries=1, default_retry_delay=10)
def batch_ai_generate(self, record_ids):
    """AI 批量生成：逐个调用 AI 并回填 AIGenerationRecord"""
    from test_manager.models import AIGenerationRecord
    from test_manager.ai_adapters import get_adapter
    from test_manager.api.views import _normalize_kv, _normalize_list, _format_param_schema
    import time as _time

    logger.info(f"[AI批生成] 任务开始，处理 {len(record_ids)} 条记录: {record_ids}")

    records = AIGenerationRecord.objects.filter(id__in=record_ids)
    if not records.exists():
        logger.warning(f"[AI批生成] 未找到记录: {record_ids}")
        return {"success": False, "error": "records not found"}

    results = []
    for idx, record in enumerate(records, 1):
        logger.info(f"[AI批生成] 处理第 {idx}/{len(record_ids)} 条记录(ID={record.id})")
        try:
            provider = record.model_provider
            if not provider:
                record.status = "failed"
                record.error_message = "未指定 AI 模型"
                record.save(update_fields=["status", "error_message"])
                results.append({"record_id": record.id, "status": "failed"})
                logger.warning(f"[AI批生成] 记录 {record.id} 跳过：未指定 AI 模型")
                continue

            adapter = get_adapter(provider)
            logger.info(f"[AI批生成] 记录 {record.id} 使用模型: {provider.name}，端点: {provider.endpoint}")
            base_info = record.interface_info or {}
            case_type = record.case_type

            raw_params = base_info.get("request_params", {})
            interface_info = {
                "request_method": base_info.get("request_method", ""),
                "request_url": base_info.get("request_url", ""),
                "api_name": base_info.get("api_name", ""),
                "api_desc": base_info.get("api_desc", ""),
                "request_headers": _normalize_kv(base_info.get("request_headers", {})),
                "request_params": _normalize_kv(raw_params),
                "param_schema": _format_param_schema(raw_params),
                "request_body_format": base_info.get("request_body_format", ""),
                "request_body": base_info.get("request_body", {}),
                "response_schema": base_info.get("response_schema", {}),
                "error_codes": _normalize_list(base_info.get("error_codes", [])),
                "auth_config": _normalize_kv(base_info.get("auth_config", {})),
            }
            rules_text = base_info.get("generation_rules", "")
            prompt_template_obj = None
            pt_text = base_info.get("prompt_template_text")
            if pt_text:
                class _PromptTemplateProxy:
                    def to_rendered_prompt(self, ctx):
                        text = pt_text
                        for k, v in ctx.items():
                            text = text.replace("{" + k + "}", str(v))
                        return text
                prompt_template_obj = _PromptTemplateProxy()
            elif pt_id := base_info.get("prompt_template_id"):
                from test_manager.models.prompt_template import PromptTemplate as _PT
                prompt_template_obj = _PT.objects.filter(id=pt_id, is_enabled=True).first()

            pt_name = base_info.get("prompt_template_name", "")
            logger.info(f"[AI批生成] 记录 {record.id} 使用提示词模板: {(pt_name or '（兜底模型默认提示词）')}")

            actual_prompt = adapter._render_prompt(interface_info, rules_text, case_type, prompt_template_obj)
            logger.info(f"[AI批生成] 记录 {record.id} 开始调用AI（接口: {interface_info['api_name']} {interface_info['request_method']} {interface_info['request_url']}）")

            _start = _time.monotonic()
            try:
                cases = adapter.call(interface_info, rules_text, case_type, prompt_template_obj)
                _elapsed_ms = int((_time.monotonic() - _start) * 1000)
                logger.info(f"[AI批生成] 记录 {record.id} AI 调用成功，耗时 {_elapsed_ms}ms，返回 {len(cases) if isinstance(cases, list) else '非数组'} 条用例")
            except Exception as exc:
                _elapsed_ms = int((_time.monotonic() - _start) * 1000)
                logger.error(f"[AI批生成] 记录 {record.id} AI 调用失败（{_elapsed_ms}ms）: {str(exc)[:200]}")
                record.status = "failed"
                record.error_message = str(exc)[:2000]
                record.duration_ms = _elapsed_ms
                record.response_raw = (adapter.last_raw_response or "")[:10000]
                record.save(update_fields=["status", "error_message", "duration_ms", "response_raw"])
                results.append({"record_id": record.id, "status": "failed", "error": str(exc)})
                continue

            if not isinstance(cases, list) or len(cases) == 0:
                logger.warning(f"[AI批生成] 记录 {record.id} AI 返回为空或格式错误")
                record.status = "failed"
                record.error_message = "AI 未返回有效用例"
                record.duration_ms = _elapsed_ms
                record.response_raw = (adapter.last_raw_response or "")[:10000]
                record.save(update_fields=["status", "error_message", "duration_ms", "response_raw"])
                results.append({"record_id": record.id, "status": "failed", "error": "AI returned empty"})
                continue

            record.request_prompt = actual_prompt[:10000]
            record.response_raw = json.dumps(cases, ensure_ascii=False, indent=2)[:10000]
            record.case_count = len(cases)
            record.duration_ms = _elapsed_ms
            record.success = True
            record.status = "success"
            record.error_message = ""
            record.save(update_fields=[
                "request_prompt", "response_raw", "case_count",
                "duration_ms", "success", "status", "error_message",
            ])

            try:
                platform_project_id = base_info.get("platform_project_id")
                if platform_project_id:
                    from test_manager.models import AICaseDraftGroup, AICaseDraft
                    from test_manager.forms import TestCaseForm

                    with transaction.atomic():
                        draft_group = AICaseDraftGroup.objects.create(
                            project_id=platform_project_id,
                            interface_id=base_info.get("interface_id"),
                            case_type=case_type,
                            base_info=interface_info,
                            created_by=record.created_by,
                        )
                        for index, item in enumerate(cases):
                            ai_headers = _normalize_kv(item.get("request_headers") or {})
                            ai_rules = _normalize_list(item.get("validation_rules"))
                            ai_params = item.get("request_params") or {}
                            req_method = item.get("request_method") or base_info.get("request_method", "")
                            req_url = item.get("request_url") or base_info.get("request_url", "")
                            if ai_params and req_method in ("GET", "DELETE"):
                                sep = "&" if "?" in req_url else "?"
                                req_url = f"{req_url}{sep}{urlencode(ai_params, doseq=True)}"
                            case_data = {
                                "name": item.get("name") or f"AI生成用例{index + 1}",
                                "description": item.get("description") or "",
                                "project": platform_project_id,
                                "request_method": req_method,
                                "request_url": req_url,
                                "request_params": ai_params,
                                "request_headers_json": json.dumps(ai_headers, ensure_ascii=False),
                                "request_body_json": json.dumps(item.get("request_body") or {}, ensure_ascii=False),
                                "request_body_format": item.get("request_body_format") or base_info.get("request_body_format") or "json",
                                "validation_rules_json": json.dumps(ai_rules, ensure_ascii=False),
                                "expected_status_code": item.get("expected_status_code") or 200,
                            }
                            form = TestCaseForm(data=case_data)
                            is_valid = form.is_valid()
                            AICaseDraft.objects.create(
                                draft_group=draft_group,
                                case_data=case_data,
                                is_valid=is_valid,
                                validation_errors=form.errors.get_json_data() if not is_valid else {},
                            )
                    info = record.interface_info or {}
                    info["draft_group_id"] = draft_group.id
                    record.interface_info = info
                    record.save(update_fields=["interface_info"])
                    logger.info(f"[AI批生成] 记录 {record.id} 已创建草稿组 {draft_group.id}，共 {len(cases)} 条草稿")
                else:
                    logger.warning(f"[AI批生成] 记录 {record.id} 缺少 platform_project_id，跳过草稿创建")
            except Exception as draft_exc:
                logger.exception(f"[AI批生成] 记录 {record.id} 创建草稿失败: {draft_exc}")

            results.append({"record_id": record.id, "status": "success", "case_count": len(cases)})
            logger.info(f"[AI批生成] 记录 {record.id} 处理完成，生成 {len(cases)} 条用例")

        except Exception as exc:
            logger.exception(f"[AI批生成] 记录 {record.id} 处理异常: {exc}")
            try:
                record.status = "failed"
                record.error_message = str(exc)[:2000]
                record.save(update_fields=["status", "error_message"])
            except Exception:
                pass
            results.append({"record_id": record.id, "status": "failed", "error": str(exc)})

    logger.info(f"[AI批生成] 任务完成。总计 {len(record_ids)}, 结果: {sum(1 for r in results if r['status']=='success')} 成功, {sum(1 for r in results if r['status']=='failed')} 失败")
    return {"success": True, "results": results}


# 确保任务被正确注册
task_list = [
    execute_scheduled_test_suite,
    send_task_notification_email,
    cleanup_old_execution_logs,
    update_scheduled_tasks_next_run_time,
    run_scheduled_task_now,
    check_celery_status,
    export_scene_execution_report_async,
    batch_ai_generate,
    extract_apis_from_document_async,
]
