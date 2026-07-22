import os
from celery import Celery

# 设置默认的Django设置模块
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "EasyTesting.settings")

app = Celery('easy_testing')

# 使用Django的设置文件配置Celery
app.config_from_object('django.conf:settings', namespace='CELERY')

# 自动发现任务
app.autodiscover_tasks()

# 定时任务配置
app.conf.beat_schedule = {
    'update-scheduled-tasks-next-run-time': {
        'task': 'test_manager.tasks.update_scheduled_tasks_next_run_time',
        'schedule': 60.0,  # 每分钟执行一次
    },
    'cleanup-old-execution-logs': {
        'task': 'test_manager.tasks.cleanup_old_execution_logs',
        'schedule': 86400.0,  # 每天执行一次
    },
    'check-zombie-scene-executions': {
        'task': 'test_manager.tasks.check_zombie_scene_executions',
        'schedule': 120.0,  # 每 2 分钟执行一次
    },
    'cleanup-old-scene-executions': {
        'task': 'test_manager.tasks.cleanup_old_scene_executions',
        'schedule': 86400.0,  # 每天执行一次
    },
    'check-ui-scheduled-tasks': {
        'task': 'test_manager.ui_automation.tasks.check_ui_scheduled_tasks',
        'schedule': 60.0,  # 每分钟检查 UI 定时任务
    },
    'check-app-scheduled-tasks': {
        'task': 'test_manager.app_automation.tasks.check_app_scheduled_tasks',
        'schedule': 60.0,  # 每分钟检查 APP 定时任务
    },
    'check-app-device-locks': {
        'task': 'test_manager.app_automation.tasks.check_and_release_expired_devices',
        'schedule': 300.0,  # 每 5 分钟检查设备锁定
    },
}

app.conf.timezone = 'Asia/Shanghai'

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
