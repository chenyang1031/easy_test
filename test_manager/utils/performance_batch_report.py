"""
性能测试批量报告生成工具

负责聚合多个性能测试任务的结果，生成整体统计报告
"""
from django.db.models import Avg, Max, Min, Sum, F, Q
from test_manager.models import PerformanceBatchTask, PerformanceBatchItem, PerformanceTestResult


def build_batch_report_dict(batch):
    """
    构建批量任务的聚合报告
    
    Args:
        batch: PerformanceBatchTask 对象
    
    Returns:
        dict: 聚合后的批量报告数据
    """
    # 获取所有成功的任务项及其结果
    successful_items = PerformanceBatchItem.objects.filter(
        batch=batch,
        status=PerformanceBatchItem.STATUS_SUCCESS
    ).select_related("performance_task")
    
    if not successful_items.exists():
        return _empty_batch_report(batch)
    
    # 收集所有任务项的数据
    all_results = []
    task_summaries = []
    
    for item in successful_items:
        # 获取该任务的所有结果数据
        results = PerformanceTestResult.objects.filter(
            task=item.performance_task
        ).order_by("timestamp")
        
        if not results.exists():
            continue
        
        # 汇总该任务的基本信息
        task_summary = {
            "task_id": item.performance_task.id,
            "task_name": item.performance_task.name,
            "interface_url": item.performance_task.interface.url,
            "method": item.performance_task.interface.method,
            "environment": item.performance_task.environment.name,
            "results": list(results.values()),
            "summary": _compute_task_summary(results),
        }
        task_summaries.append(task_summary)
        
        # 收集所有采样点用于全局聚合
        for result in results:
            result.task_id = item.performance_task.id
            result.interface_url = item.performance_task.interface.url
            result.environment_name = item.performance_task.environment.name
            all_results.append(result)
    
    # 生成整体聚合报告
    overall_report = _compute_overall_report(all_results, task_summaries)
    
    return {
        "batch_id": batch.id,
        "batch_name": batch.name,
        "status": batch.status,
        "total_tasks": batch.total_tasks,
        "completed_tasks": batch.completed_tasks,
        "successful_tasks": batch.successful_tasks,
        "failed_tasks": batch.failed_tasks,
        "success_rate_percent": batch.success_rate,
        "execute_mode": batch.execute_mode,
        "started_at": batch.started_at,
        "finished_at": batch.finished_at,
        "overall_report": overall_report,
        "task_summaries": task_summaries,
    }


def _compute_task_summary(results):
    """
    计算单个任务的任务摘要统计
    
    Args:
        results: PerformanceTestResult QuerySet
    
    Returns:
        dict: 任务摘要统计数据
    """
    summary = {
        "sample_count": results.count(),
        "duration_seconds": 0,
        "max_rps": 0,
        "avg_rps": 0,
        "avg_response_time_50_ms": 0,
        "avg_response_time_90_ms": 0,
        "max_active_users": 0,
        "avg_failure_rate_percent": 0,
        "avg_p95_ms": 0,
        "avg_p99_ms": 0,
        "max_p95_ms": 0,
        "max_p99_ms": 0,
        "max_response_time_ms": 0,
    }
    
    if results.count() == 0:
        return summary
    
    # 计算时间跨度
    first_result = results.first()
    last_result = results.last()
    if first_result and last_result:
        from datetime import timedelta
        duration = (last_result.timestamp - first_result.timestamp).total_seconds()
        summary["duration_seconds"] = int(duration)
    
    # 聚合统计
    summary_data = results.aggregate(
        max_rps=Max("requests_per_second"),
        avg_rps=Avg("requests_per_second"),
        avg_rtt50=Avg("response_time_50"),
        avg_rtt90=Avg("response_time_90"),
        max_users=Max("active_users"),
        avg_failure=Avg("failure_rate"),
        avg_p95=Avg("p95"),
        avg_p99=Avg("p99"),
        max_p95=Max("p95"),
        max_p99=Max("p99"),
        max_rt=Max("max_response_time"),
    )
    
    summary["max_rps"] = round(summary_data.get("max_rps", 0) or 0, 2)
    summary["avg_rps"] = round(summary_data.get("avg_rps", 0) or 0, 2)
    summary["avg_response_time_50_ms"] = round(summary_data.get("avg_rtt50", 0) or 0, 2)
    summary["avg_response_time_90_ms"] = round(summary_data.get("avg_rtt90", 0) or 0, 2)
    summary["max_active_users"] = int(summary_data.get("max_users", 0) or 0)
    summary["avg_failure_rate_percent"] = round(summary_data.get("avg_failure", 0) or 0, 2)
    summary["avg_p95_ms"] = round(summary_data.get("avg_p95", 0) or 0, 2)
    summary["avg_p99_ms"] = round(summary_data.get("avg_p99", 0) or 0, 2)
    summary["max_p95_ms"] = round(summary_data.get("max_p95", 0) or 0, 2)
    summary["max_p99_ms"] = round(summary_data.get("max_p99", 0) or 0, 2)
    summary["max_response_time_ms"] = round(summary_data.get("max_rt", 0) or 0, 2)
    
    return summary


def _compute_overall_report(all_results, task_summaries):
    """
    计算整体聚合报告
    
    Args:
        all_results: 所有采样结果列表
        task_summaries: 各任务摘要列表
    
    Returns:
        dict: 整体聚合报告
    """
    report = {
        "total_samples": len(all_results),
        "total_tasks": len(task_summaries),
        "unique_interfaces": set(),
        "environments": set(),
        "aggregated_metrics": {},
        "task_performance_comparison": [],
        "error_analysis": {},
    }
    
    if not all_results:
        return report
    
    # 提取唯一的接口和环境
    interfaces = set()
    environments = set()
    error_stats = {}
    
    for result in all_results:
        interfaces.add(getattr(result, "interface_url", "unknown"))
        environments.add(getattr(result, "environment_name", "unknown"))
        
        # 收集错误分类
        error_class = getattr(result, "error_classification", {})
        if error_class:
            for key, count in error_class.items():
                error_stats[key] = error_stats.get(key, 0) + count
    
    report["unique_interfaces"] = sorted(list(interfaces))
    report["environments"] = sorted(list(environments))
    
    # 聚合指标统计（加权平均）
    total_weight = 0
    weighted_metrics = {}
    
    for summary in task_summaries:
        sample_count = summary["summary"]["sample_count"]
        if sample_count == 0:
            continue
        
        metrics = summary["summary"]
        weight = sample_count
        total_weight += weight
        
        # 累加各项指标的加权和
        metric_keys = [
            ("max_rps", "max_rps"),
            ("avg_rps", "avg_rps"),
            ("avg_response_time_50_ms", "rt50"),
            ("avg_response_time_90_ms", "rt90"),
            ("max_active_users", "users"),
            ("avg_failure_rate_percent", "failure"),
            ("avg_p95_ms", "p95"),
            ("avg_p99_ms", "p99"),
            ("max_p95_ms", "max_p95"),
            ("max_p99_ms", "max_p99"),
            ("max_response_time_ms", "max_rt"),
        ]
        
        for source_key, target_key in metric_keys:
            value = metrics.get(source_key, 0) or 0
            if target_key not in weighted_metrics:
                weighted_metrics[target_key] = {"sum": 0, "weight_sum": 0}
            weighted_metrics[target_key]["sum"] += value * weight
            weighted_metrics[target_key]["weight_sum"] += weight
    
    # 计算最终聚合值
    if total_weight > 0:
        aggregated = {}
        for key, data in weighted_metrics.items():
            if data["weight_sum"] > 0:
                aggregated[key] = round(data["sum"] / data["weight_sum"], 2)
        
        report["aggregated_metrics"] = aggregated
    
    # 任务性能对比
    for summary in task_summaries:
        report["task_performance_comparison"].append({
            "task_name": summary["task_name"],
            "interface": summary["interface_url"],
            "method": summary["method"],
            "env": summary["environment"],
            **summary["summary"],
        })
    
    # 错误分析
    report["error_analysis"] = {
        "total_errors": sum(error_stats.values()),
        "by_type": error_stats,
    }
    
    # 按环境分组统计
    env_groups = {}
    for summary in task_summaries:
        env = summary["environment"]
        if env not in env_groups:
            env_groups[env] = []
        env_groups[env].append(summary)
    
    report["environment_breakdown"] = {}
    for env, tasks in env_groups.items():
        env_report = {
            "env": env,
            "task_count": len(tasks),
            "total_samples": sum(t["summary"]["sample_count"] for t in tasks),
        }
        report["environment_breakdown"][env] = env_report
    
    return report


def _empty_batch_report(batch):
    """
    返回空批量报告（当没有成功执行的任务时）
    
    Args:
        batch: PerformanceBatchTask 对象
    
    Returns:
        dict: 空的批量报告
    """
    return {
        "batch_id": batch.id,
        "batch_name": batch.name,
        "status": batch.status,
        "total_tasks": batch.total_tasks,
        "completed_tasks": batch.completed_tasks,
        "successful_tasks": batch.successful_tasks,
        "failed_tasks": batch.failed_tasks,
        "success_rate_percent": batch.success_rate,
        "execute_mode": batch.execute_mode,
        "started_at": batch.started_at,
        "finished_at": batch.finished_at,
        "overall_report": {
            "total_samples": 0,
            "total_tasks": 0,
            "unique_interfaces": [],
            "environments": [],
            "aggregated_metrics": {},
            "task_performance_comparison": [],
            "error_analysis": {
                "total_errors": 0,
                "by_type": {},
            },
            "environment_breakdown": {},
        },
        "task_summaries": [],
    }


def serialize_batch_report_response(batch, report):
    """
    序列化批量报告响应
    
    Args:
        batch: PerformanceBatchTask 对象
        report: 批量报告字典
    
    Returns:
        dict: API 响应格式的报告
    """
    payload = {
        "batch_id": batch.id,
        "batch_name": batch.name,
        "status": batch.status,
        "status_label": dict(PerformanceBatchTask.STATUS_CHOICES)[batch.status],
        "created_at": batch.created_at.isoformat() if batch.created_at else None,
        "started_at": batch.started_at.isoformat() if batch.started_at else None,
        "finished_at": batch.finished_at.isoformat() if batch.finished_at else None,
        "report": report,
    }
    
    # 添加进度和成功率
    payload["progress_percent"] = batch.progress
    payload["success_rate_percent"] = batch.success_rate
    
    return payload
