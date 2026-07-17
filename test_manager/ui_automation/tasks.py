"""
UI自动化 Celery 异步任务
"""
import logging
from celery import shared_task
from django.utils import timezone

logger = logging.getLogger('test_manager.ui_automation')


@shared_task(bind=True, max_retries=1, default_retry_delay=10)
def execute_ui_test_case(self, record_id, env_id):
    """
    执行单个 UI 测试用例

    Args:
        record_id: UiExecutionRecord ID
        env_id: UiEnvironmentConfig ID
    """
    from .models import UiExecutionRecord, UiEnvironmentConfig, UiBatchExecutionRecord
    from .executor import UIExecutor

    try:
        record = UiExecutionRecord.objects.select_related('test_case', 'batch').get(pk=record_id)
        env = UiEnvironmentConfig.objects.get(pk=env_id)
    except (UiExecutionRecord.DoesNotExist, UiEnvironmentConfig.DoesNotExist) as e:
        logger.error(f"记录或环境不存在: {e}")
        return {'status': 'error', 'message': str(e)}

    record.status = 1  # 执行中
    record.start_time = timezone.now()
    record.save(update_fields=['status', 'start_time'])

    try:
        executor = UIExecutor(env)
        result = executor.execute_test_case(record.test_case)

        record.status = 2 if result['success'] else 3
        record.step_results = result.get('step_results')
        record.screenshots = result.get('screenshots')
        record.log = result.get('log', '')
        record.error_message = result.get('error', '')
        record.video_path = result.get('video_path', '')
        record.trace_path = result.get('trace_path', '')
        record.end_time = timezone.now()
        record.duration = (record.end_time - record.start_time).total_seconds()
        record.save()

        # 更新批次统计
        _update_batch_stats(record.batch)

        return {'status': 'success' if result['success'] else 'failed', 'record_id': record_id}

    except Exception as e:
        logger.exception(f"执行测试用例失败: {e}")
        record.status = 3
        record.error_message = str(e)
        record.end_time = timezone.now()
        record.duration = (record.end_time - record.start_time).total_seconds()
        record.save()
        _update_batch_stats(record.batch)
        return {'status': 'error', 'message': str(e)}


@shared_task(bind=True, max_retries=1, default_retry_delay=10)
def execute_ui_test_batch(self, batch_id):
    """
    执行批量测试任务（遍历批次内所有待执行记录）

    Args:
        batch_id: UiBatchExecutionRecord ID
    """
    from .models import UiBatchExecutionRecord, UiExecutionRecord, UiEnvironmentConfig
    from .executor import UIExecutor

    try:
        batch = UiBatchExecutionRecord.objects.get(pk=batch_id)
    except UiBatchExecutionRecord.DoesNotExist:
        logger.error(f"批次 {batch_id} 不存在")
        return {'status': 'error', 'message': '批次不存在'}

    # 获取所有待执行的记录
    pending_records = UiExecutionRecord.objects.filter(
        batch=batch, status=1
    ).select_related('test_case')

    if not pending_records.exists():
        batch.status = 4  # 部分成功（没有可执行的）
        batch.end_time = timezone.now()
        batch.save()
        return {'status': 'no_pending_records'}

    # 取第一条记录的环境（批量执行统一使用同一环境）
    # 环境信息在触发时传入，这里从 batch 关联获取
    # 简化处理：使用默认环境
    env = None
    try:
        first_record = pending_records.first()
        # 尝试从环境配置获取，这里简化为使用默认环境
        env = UiEnvironmentConfig.objects.filter(
            project=batch.project, is_default=True
        ).first()
        if not env:
            env = UiEnvironmentConfig.objects.filter(project=batch.project).first()
    except Exception:
        pass

    if not env:
        # 没有环境配置，标记所有记录为失败
        for record in pending_records:
            record.status = 3
            record.error_message = '未找到可用的环境配置'
            record.end_time = timezone.now()
            record.save()
        batch.status = 3
        batch.end_time = timezone.now()
        batch.save()
        return {'status': 'error', 'message': '未找到环境配置'}

    executor = UIExecutor(env)

    for record in pending_records:
        record.start_time = timezone.now()
        record.save(update_fields=['start_time'])

        try:
            result = executor.execute_test_case(record.test_case)
            record.status = 2 if result['success'] else 3
            record.step_results = result.get('step_results')
            record.screenshots = result.get('screenshots')
            record.log = result.get('log', '')
            record.error_message = result.get('error', '')
        except Exception as e:
            record.status = 3
            record.error_message = str(e)
            logger.exception(f"执行用例 {record.test_case.name} 失败: {e}")

        record.end_time = timezone.now()
        record.duration = (record.end_time - record.start_time).total_seconds()
        record.save()

    _update_batch_stats(batch)
    return {'status': 'completed', 'batch_id': batch_id}


@shared_task(bind=True, max_retries=1)
def run_ai_browser_task(self, record_id):
    """
    运行 AI 浏览器任务

    Args:
        record_id: UiAIExecutionRecord ID
    """
    from .models import UiAIExecutionRecord
    from .ai_agent import AIBrowserAgent

    try:
        record = UiAIExecutionRecord.objects.select_related('ai_case').get(pk=record_id)
    except UiAIExecutionRecord.DoesNotExist:
        logger.error(f"AI执行记录 {record_id} 不存在")
        return {'status': 'error', 'message': '记录不存在'}

    record.status = 'running'
    record.start_time = timezone.now()
    record.save(update_fields=['status', 'start_time'])

    try:
        agent = AIBrowserAgent()
        result = agent.run_task(
            task_description=record.ai_case.task_description,
            record=record,
        )

        record.status = 'passed' if result.get('success') else 'failed'
        record.planned_tasks = result.get('planned_tasks')
        record.steps_completed = result.get('steps_completed')
        record.screenshots_sequence = result.get('screenshots', [])
        record.logs = result.get('logs', '')
        record.token_cost = result.get('token_cost', 0)
        record.end_time = timezone.now()
        record.duration = (record.end_time - record.start_time).total_seconds()
        record.save()

        return {'status': record.status, 'record_id': record_id}

    except Exception as e:
        logger.exception(f"AI浏览器任务失败: {e}")
        record.status = 'failed'
        record.logs = str(e)
        record.end_time = timezone.now()
        record.duration = (record.end_time - record.start_time).total_seconds()
        record.save()
        return {'status': 'error', 'message': str(e)}


@shared_task(bind=True, max_retries=1)
def run_ui_scheduled_task(self, task_id):
    """
    执行 UI 定时任务

    Args:
        task_id: UiScheduledTask ID
    """
    from .models import UiScheduledTask, UiBatchExecutionRecord, UiExecutionRecord

    try:
        task = UiScheduledTask.objects.get(pk=task_id)
    except UiScheduledTask.DoesNotExist:
        logger.error(f"定时任务 {task_id} 不存在")
        return {'status': 'error', 'message': '任务不存在'}

    if not task.is_active:
        return {'status': 'skipped', 'message': '任务已暂停'}

    test_cases = task.test_cases.all()
    if not test_cases.exists():
        logger.warning(f"定时任务 {task_id} 没有关联的测试用例")
        return {'status': 'no_cases'}

    env = task.environment
    if not env:
        logger.error(f"定时任务 {task_id} 没有配置环境")
        return {'status': 'error', 'message': '未配置环境'}

    # 创建批次记录
    batch = UiBatchExecutionRecord.objects.create(
        project=task.project,
        name=f"定时任务: {task.name}",
        total_cases=test_cases.count(),
        status=1,
        trigger_type='scheduled',
        start_time=timezone.now(),
        created_by=task.created_by,
    )

    for tc in test_cases:
        UiExecutionRecord.objects.create(
            batch=batch,
            test_case=tc,
            executor='system',
            status=1,
            trigger_type='scheduled',
            start_time=timezone.now(),
        )

    # 更新任务统计
    task.total_runs += 1
    task.last_run_at = timezone.now()
    task.save(update_fields=['total_runs', 'last_run_at'])

    # 提交批量执行
    execute_ui_test_batch.delay(batch.id)

    return {'status': 'dispatched', 'batch_id': batch.id}


def _update_batch_stats(batch):
    """更新批次执行统计"""
    from .models import UiExecutionRecord
    from django.db.models import Count

    stats = UiExecutionRecord.objects.filter(batch=batch).values('status').annotate(count=Count('id'))
    passed = sum(s['count'] for s in stats if s['status'] == 2)
    failed = sum(s['count'] for s in stats if s['status'] == 3)

    batch.passed_cases = passed
    batch.failed_cases = failed

    # 判断是否全部完成
    total = batch.total_cases
    completed = passed + failed
    if completed >= total:
        batch.end_time = timezone.now()
        batch.duration = (batch.end_time - batch.start_time).total_seconds() if batch.start_time else 0
        if failed == 0:
            batch.status = 2  # 全部成功
        elif passed == 0:
            batch.status = 3  # 全部失败
        else:
            batch.status = 4  # 部分成功

    batch.save()


@shared_task
def check_ui_scheduled_tasks():
    """
    定期检查 UI 定时任务，触发到期的任务。
    由 celery-beat 每分钟调用一次。
    """
    from .models import UiScheduledTask

    now = timezone.now()
    active_tasks = UiScheduledTask.objects.filter(is_active=True)

    for task in active_tasks:
        should_run = False

        if task.trigger_type == 'once' and task.run_at:
            # 单次执行：检查是否到期
            if task.run_at <= now and task.total_runs == 0:
                should_run = True

        elif task.trigger_type == 'interval' and task.interval_seconds:
            # 固定间隔：检查上次执行时间
            if task.last_run_at:
                from datetime import timedelta
                next_run = task.last_run_at + timedelta(seconds=task.interval_seconds)
                if next_run <= now:
                    should_run = True
            else:
                should_run = True  # 从未执行过

        elif task.trigger_type == 'cron' and task.cron_expression:
            # Cron 表达式（简化检查）
            try:
                from croniter import croniter
                if task.last_run_at:
                    cron = croniter(task.cron_expression, task.last_run_at)
                    next_run = cron.get_next(type(now))
                    if next_run <= now:
                        should_run = True
                else:
                    should_run = True
            except ImportError:
                # croniter 未安装，跳过 cron 任务
                logger.debug("croniter 未安装，跳过 cron 类型定时任务")
            except Exception as e:
                logger.warning(f"Cron 表达式解析失败: {e}")

        if should_run:
            try:
                run_ui_scheduled_task.delay(task.id)
                logger.info(f"触发 UI 定时任务: {task.name} (ID={task.id})")
            except Exception as e:
                logger.error(f"触发定时任务失败: {e}")
