#!/usr/bin/env python3
"""
全链路验证测试脚本
验证从上传日志到获取解析结果和聚合事件的完整流程
"""
import asyncio
import os
import sys
import uuid
import time
import requests
import json
from datetime import datetime

# 设置 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

try:
    import matplotlib
    matplotlib.use('Agg')  # 使用非交互式后端
    import matplotlib.pyplot as plt
    from matplotlib.dates import DateFormatter
    CAN_PLOT = True
except ImportError:
    CAN_PLOT = False
    print("⚠️  matplotlib 未安装，将跳过曲线绘制")

from latency.schemas.log import LogFileModel, LogKnowledgeModel
from latency.database.managers.log_file import LogFileManager
from latency.database.managers.log_knowledge import LogKnowledgeManager
from latency.database.engine import AsyncSQLiteSingleton
from latency.ENUM.task import TaskStatusEnum


class TestResult:
    """测试结果收集器"""
    def __init__(self):
        self.steps = []
        self.log_parse_results = []
        self.aggregated_events = []
        self.latency_metrics = []
        self.errors = []
    
    def add_step(self, name, status, message, data=None):
        self.steps.append({
            "name": name,
            "status": status,
            "message": message,
            "data": data,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
    
    def add_error(self, step, error):
        self.errors.append({
            "step": step,
            "error": str(error),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })


async def setup_test_data() -> tuple[str, str]:
    """设置测试数据：创建 log_knowledge 和 log_file"""
    db = AsyncSQLiteSingleton()
    await db.init_database()
    
    # 创建 log_knowledge
    kb_id = str(uuid.uuid4())[:8]
    kb_model = LogKnowledgeModel(
        id=kb_id,
        image_bytes=b"",
        name="test_kb_full_link",
        description="全链路测试知识库",
    )
    await LogKnowledgeManager.add_log_kb(kb_model)
    
    return kb_id


def upload_log_files(kb_id: str, log_dir: str, parse_config=None) -> dict:
    """通过 API 上传日志文件"""
    url = f"http://localhost:9772/log_file/{kb_id}"
    
    payload = {
        "upload_log_file_configs": [
            {
                "name": "test_log",
                "source_type": "local",
                "source": log_dir
            }
        ]
    }
    
    if parse_config:
        payload["parse_config"] = parse_config
    
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": str(e)}


def query_task_status(task_id: str) -> tuple[str, str]:
    """查询任务状态，返回(status, error_message)"""
    url = f"http://localhost:9772/task/{task_id}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        result = data.get("result")
        
        if not result:
            return "未知", "API 返回无 result 字段"
        
        task = result.get("task")
        if not task:
            return "未知", f"任务 {task_id} 不存在或已被删除"
        
        status = task.get("status")
        if status is None:
            return "未知", "task 中 status 字段为 None"
        
        return status, None
        
    except requests.exceptions.ConnectionError:
        return "未知", "无法连接到 API 服务"
    except requests.exceptions.Timeout:
        return "未知", "请求超时"
    except Exception as e:
        return "未知", f"请求异常: {str(e)}"


def get_task_id_by_log_file_id(log_file_id: str) -> str | None:
    """通过日志文件ID获取任务ID"""
    url = "http://localhost:9772/task/list"
    payload = {
        "page_num": 1,
        "page_cnt": 100
    }
    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        tasks = data.get("result", {}).get("tasks", [])
        for task in tasks:
            if task.get("op_id") == log_file_id:
                return task.get("id")
        
        return None
    except Exception as e:
        print(f"❌ 查询任务列表失败: {e}")
        return None


def wait_for_task_completion(task_id: str, timeout=30000) -> bool:
    """等待任务完成"""
    print(f"\n等待任务 {task_id} 完成（最多 {timeout} 秒）")
    for i in range(timeout):
        status, error = query_task_status(task_id)
        
        if error:
            print(f"\r第 {i+1:3d} 秒 - {error}", end="", flush=True)
        else:
            print(f"\r第 {i+1:3d} 秒 - 任务状态: {status}", end="", flush=True)
        
        if status in ["successful", "successful_pending_remove"]:
            print("\n✅ 任务完成！")
            return True
        
        if status == "failed":
            print("\n❌ 任务失败！")
            return False
        
        time.sleep(1)
    
    print("\n❌ 任务超时！")
    return False


def get_log_parse_results(kb_id: str) -> dict:
    """获取日志解析结果"""
    url = "http://localhost:9772/log_parse_result/list"
    payload = {
        "kb_id": kb_id,
        "page_num": 1,
        "page_cnt": 100
    }
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": str(e)}


def get_aggregated_events(kb_id: str) -> dict:
    """获取聚合事件"""
    url = "http://localhost:9772/aggregated_event/list"
    payload = {
        "kb_id": kb_id,
        "page_num": 1,
        "page_cnt": 100
    }
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": str(e)}


def get_latency_metrics(max_points: int = -1, **kwargs) -> dict:
    """获取延迟指标时间曲线数据"""
    url = "http://localhost:9772/log_parse_result/metrics/latency"
    payload = {
        "max_points": max_points,  # -1 表示获取全部数据
        "sort_by": "timestamp",
        "sort_order": "asc"
    }
    # 添加可选参数
    for key in ["host", "src_ip", "dst_ip", "start_time", "end_time", "operation"]:
        if key in kwargs:
            payload[key] = kwargs[key]
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": str(e)}


def plot_latency_curve(metrics_data: list, output_path: str):
    """绘制延迟曲线"""
    if not CAN_PLOT:
        print("⚠️  matplotlib 未安装，跳过曲线绘制")
        return False
    
    if not metrics_data:
        print("⚠️  没有数据可绘制")
        return False
    
    try:
        # 准备数据
        timestamps = []
        total_latency = []
        urma_latency = []
        query_meta_latency = []
        
        for item in metrics_data:
            timestamps.append(datetime.strptime(item["timestamp"], "%Y-%m-%d %H:%M:%S"))
            total_latency.append(item.get("total_latency_ms", 0))
            urma_latency.append(item.get("urma_total_latency_ms", 0))
            query_meta_latency.append(item.get("worker_query_meta_latency_ms", 0))
        
        # 创建图表
        plt.figure(figsize=(12, 6))
        
        plt.plot(timestamps, total_latency, label='Total Latency (ms)', color='#667eea', linewidth=2)
        plt.plot(timestamps, urma_latency, label='URMA Latency (ms)', color='#f093fb', linewidth=2)
        plt.plot(timestamps, query_meta_latency, label='Query Meta Latency (ms)', color='#4ade80', linewidth=2)
        
        # 设置格式
        plt.gcf().autofmt_xdate()
        plt.gca().xaxis.set_major_formatter(DateFormatter('%Y-%m-%d %H:%M'))
        
        plt.title('Latency Metrics Over Time', fontsize=14)
        plt.xlabel('Time', fontsize=12)
        plt.ylabel('Latency (ms)', fontsize=12)
        plt.legend(fontsize=10)
        plt.grid(True, alpha=0.3)
        
        # 保存图表
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()
        
        print(f"✅ 延迟曲线已保存: {output_path}")
        return True
    except Exception as e:
        print(f"❌ 绘制曲线失败: {e}")
        return False


def generate_html_report(test_result: TestResult, output_path: str):
    """生成 HTML 报告"""
    html_template = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>全链路测试报告</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f7fa; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; text-align: center; }}
        .container {{ max-width: 1200px; margin: 20px auto; padding: 0 20px; }}
        .card {{ background: white; border-radius: 8px; box-shadow: 0 2px 12px rgba(0,0,0,0.08); margin-bottom: 20px; overflow: hidden; }}
        .card-header {{ padding: 15px 20px; background: #f8f9fa; border-bottom: 1px solid #e9ecef; font-weight: 600; }}
        .card-body {{ padding: 20px; }}
        .step {{ display: flex; align-items: flex-start; margin-bottom: 15px; padding: 12px; border-radius: 6px; }}
        .step:last-child {{ margin-bottom: 0; }}
        .step-success {{ background: #d4edda; border-left: 4px solid #28a745; }}
        .step-failed {{ background: #f8d7da; border-left: 4px solid #dc3545; }}
        .step-pending {{ background: #fff3cd; border-left: 4px solid #ffc107; }}
        .step-icon {{ font-size: 20px; margin-right: 12px; }}
        .step-content {{ flex: 1; }}
        .step-title {{ font-weight: 600; margin-bottom: 4px; }}
        .step-message {{ color: #666; font-size: 14px; }}
        .step-time {{ font-size: 12px; color: #999; }}
        .data-section {{ margin-top: 15px; padding-top: 15px; border-top: 1px dashed #e9ecef; }}
        .data-title {{ font-size: 14px; font-weight: 600; margin-bottom: 10px; }}
        .data-json {{ background: #f8f9fa; padding: 12px; border-radius: 4px; font-family: 'Consolas', 'Monaco', monospace; font-size: 13px; overflow-x: auto; white-space: pre-wrap; word-break: break-all; }}
        .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 15px; margin-bottom: 20px; }}
        .stat-card {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 8px; text-align: center; }}
        .stat-value {{ font-size: 32px; font-weight: 700; }}
        .stat-label {{ font-size: 14px; opacity: 0.9; }}
        .table {{ width: 100%; border-collapse: collapse; margin-top: 15px; }}
        .table th, .table td {{ padding: 12px; text-align: left; border-bottom: 1px solid #e9ecef; }}
        .table th {{ background: #f8f9fa; font-weight: 600; }}
        .table tr:hover {{ background: #f8f9fa; }}
        .error-list {{ list-style: none; }}
        .error-item {{ background: #f8d7da; padding: 10px; border-radius: 4px; margin-bottom: 8px; color: #721c24; }}
        .timestamp {{ font-size: 12px; color: #999; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>全链路测试报告</h1>
        <p>生成时间: {generate_time}</p>
    </div>
    
    <div class="container">
        <!-- 统计概览 -->
        <div class="card">
            <div class="card-header">📊 测试概览</div>
            <div class="card-body">
                <div class="stats">
                    <div class="stat-card">
                        <div class="stat-value">{success_count}</div>
                        <div class="stat-label">成功步骤</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">{failed_count}</div>
                        <div class="stat-label">失败步骤</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">{parse_count}</div>
                        <div class="stat-label">解析结果数</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">{event_count}</div>
                        <div class="stat-label">聚合事件数</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">{metrics_count}</div>
                        <div class="stat-label">延迟指标数</div>
                    </div>
                </div>
            </div>
        </div>

        <!-- 测试步骤 -->
        <div class="card">
            <div class="card-header">📝 测试步骤</div>
            <div class="card-body">
                {steps_html}
            </div>
        </div>

        <!-- 解析结果 -->
        <div class="card">
            <div class="card-header">📋 日志解析结果</div>
            <div class="card-body">
                {parse_results_html}
            </div>
        </div>

        <!-- 聚合事件 -->
        <div class="card">
            <div class="card-header">🔍 聚合事件</div>
            <div class="card-body">
                {events_html}
            </div>
        </div>

        <!-- 延迟指标 -->
        <div class="card">
            <div class="card-header">📈 延迟指标</div>
            <div class="card-body">
                {metrics_html}
            </div>
        </div>

        <!-- 错误信息 -->
        {errors_html}
    </div>
</body>
</html>
    """
    
    # 统计数据
    success_count = sum(1 for s in test_result.steps if s["status"] == "success")
    failed_count = sum(1 for s in test_result.steps if s["status"] == "failed")
    parse_count = len(test_result.log_parse_results)
    event_count = len(test_result.aggregated_events)
    metrics_count = len(test_result.latency_metrics)
    
    # 生成步骤 HTML
    steps_html = ""
    for step in test_result.steps:
        status_class = {
            "success": "step-success",
            "failed": "step-failed",
            "pending": "step-pending"
        }.get(step["status"], "step-pending")
        
        icon = {
            "success": "✅",
            "failed": "❌",
            "pending": "⏳"
        }.get(step["status"], "⏳")
        
        data_html = ""
        if step["data"]:
            data_str = json.dumps(step["data"], ensure_ascii=False, indent=2)
            data_html = f"""
            <div class="data-section">
                <div class="data-title">响应数据</div>
                <div class="data-json">{data_str}</div>
            </div>
            """
        
        steps_html += f"""
        <div class="step {status_class}">
            <div class="step-icon">{icon}</div>
            <div class="step-content">
                <div class="step-title">{step['name']}</div>
                <div class="step-message">{step['message']}</div>
                <div class="step-time">时间: {step['timestamp']}</div>
                {data_html}
            </div>
        </div>
        """
    
    # 生成解析结果 HTML
    if test_result.log_parse_results:
        parse_results_html = f"""
        <table class="table">
            <thead>
                <tr>
                    <th>ID</th>
                    <th>源IP</th>
                    <th>目标IP</th>
                    <th>延迟(ms)</th>
                    <th>时间</th>
                    <th>类型</th>
                </tr>
            </thead>
            <tbody>
        """
        for result in test_result.log_parse_results[:20]:  # 最多显示20条
            parse_results_html += f"""
            <tr>
                <td>{result.get('id', '')}</td>
                <td>{result.get('src_ip', '')}</td>
                <td>{result.get('dst_ip', '')}</td>
                <td>{result.get('elapsed_ms', '')}</td>
                <td>{result.get('timestamp', '')}</td>
                <td>{result.get('entry_type', '')}</td>
            </tr>
            """
        parse_results_html += "</tbody></table>"
        if len(test_result.log_parse_results) > 20:
            parse_results_html += f"<p style='margin-top:10px;color:#666'>仅显示前20条，共{len(test_result.log_parse_results)}条</p>"
    else:
        parse_results_html = "<p style='color:#999'>暂无解析结果</p>"
    
    # 生成聚合事件 HTML
    if test_result.aggregated_events:
        events_html = f"""
        <table class="table">
            <thead>
                <tr>
                    <th>ID</th>
                    <th>源IP</th>
                    <th>目标IP</th>
                    <th>事件类型</th>
                    <th>次数</th>
                    <th>平均延迟(ms)</th>
                </tr>
            </thead>
            <tbody>
        """
        for event in test_result.aggregated_events[:20]:
            events_html += f"""
            <tr>
                <td>{event.get('id', '')}</td>
                <td>{event.get('src_ip', '')}</td>
                <td>{event.get('dst_ip', '')}</td>
                <td>{event.get('event_type', '')}</td>
                <td>{event.get('count', '')}</td>
                <td>{event.get('avg_elapsed_ms', '')}</td>
            </tr>
            """
        events_html += "</tbody></table>"
        if len(test_result.aggregated_events) > 20:
            events_html += f"<p style='margin-top:10px;color:#666'>仅显示前20条，共{len(test_result.aggregated_events)}条</p>"
    else:
        events_html = "<p style='color:#999'>暂无聚合事件</p>"
    
    # 生成延迟指标 HTML
    if test_result.latency_metrics:
        metrics_html = f"""
        <table class="table">
            <thead>
                <tr>
                    <th>时间</th>
                    <th>总延迟(ms)</th>
                    <th>URMA延迟(ms)</th>
                    <th>Query Meta延迟(ms)</th>
                </tr>
            </thead>
            <tbody>
        """
        for metric in test_result.latency_metrics[:20]:  # 最多显示20条
            metrics_html += f"""
            <tr>
                <td>{metric.get('timestamp', '')}</td>
                <td>{metric.get('total_latency_ms', '')}</td>
                <td>{metric.get('urma_total_latency_ms', '')}</td>
                <td>{metric.get('worker_query_meta_latency_ms', '')}</td>
            </tr>
            """
        metrics_html += "</tbody></table>"
        if len(test_result.latency_metrics) > 20:
            metrics_html += f"<p style='margin-top:10px;color:#666'>仅显示前20条，共{len(test_result.latency_metrics)}条</p>"
    else:
        metrics_html = "<p style='color:#999'>暂无延迟指标数据</p>"
    
    # 生成错误信息 HTML
    if test_result.errors:
        errors_html = f"""
        <div class="card">
            <div class="card-header">⚠️ 错误信息</div>
            <div class="card-body">
                <ul class="error-list">
        """
        for error in test_result.errors:
            errors_html += f"""
            <li class="error-item">
                <strong>{error['step']}</strong>: {error['error']}
                <div class="timestamp">{error['timestamp']}</div>
            </li>
            """
        errors_html += "</ul></div></div>"
    else:
        errors_html = ""
    
    # 填充模板
    html_content = html_template.format(
        generate_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        success_count=success_count,
        failed_count=failed_count,
        parse_count=parse_count,
        event_count=event_count,
        metrics_count=metrics_count,
        steps_html=steps_html,
        parse_results_html=parse_results_html,
        events_html=events_html,
        metrics_html=metrics_html,
        errors_html=errors_html
    )
    
    # 写入文件
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)


async def main():
    test_result = TestResult()
    log_dir = r"D:\test_log_1"  # 需要修改为实际的日志目录
    output_html = f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
    
    print("=" * 70)
    print("全链路验证测试")
    print("=" * 70)
    
    kb_id = None
    log_file_id = None
    task_id = None
    
    try:
        # 1. 设置测试数据
        print("\n[Step 1] 设置测试数据")
        try:
            kb_id = await setup_test_data()
            test_result.add_step("设置测试数据", "success", f"创建知识库成功: {kb_id}")
            print(f"✅ 创建知识库: {kb_id}")
        except Exception as e:
            test_result.add_step("设置测试数据", "failed", str(e))
            test_result.add_error("设置测试数据", e)
            print(f"❌ 设置测试数据失败: {e}")
            print("继续执行后续步骤...")
        
        # 2. 上传日志文件
        print("\n[Step 2] 上传日志文件")
        log_file_ids = []
        try:
            if not kb_id:
                raise Exception("知识库ID为空，无法上传")
            
            # 可选：添加时间过滤配置

            result = upload_log_files(kb_id, log_dir)
            
            if "error" in result:
                raise Exception(result["error"])
            
            log_file_ids = result.get("result", {}).get("log_file_ids", [])
            test_result.add_step("上传日志文件", "success", f"上传成功，文件ID: {log_file_ids}", result)
            print(f"✅ 上传日志文件成功: {log_file_ids}")
            
            if log_file_ids:
                log_file_id = log_file_ids[0]
                print(f"✅ 日志文件ID: {log_file_id}")
            else:
                raise Exception("未返回 log_file_ids")
        except Exception as e:
            test_result.add_step("上传日志文件", "failed", str(e))
            test_result.add_error("上传日志文件", e)
            print(f"❌ 上传日志文件失败: {e}")
            print("继续执行后续步骤...")
        
        # 3. 查询对应的任务ID
        print("\n[Step 3] 查询对应的任务ID")
        try:
            if not log_file_id:
                raise Exception("日志文件ID为空，无法查询任务")
            
            print("等待任务创建...")
            task_id = None
            for i in range(10):
                task_id = get_task_id_by_log_file_id(log_file_id)
                if task_id:
                    break
                print(f"\r第 {i+1} 秒 - 等待任务创建...", end="", flush=True)
                time.sleep(1)
            
            if not task_id:
                raise Exception("10秒内未找到对应任务")
            
            test_result.add_step("查询任务ID", "success", f"找到任务ID: {task_id}")
            print(f"\n✅ 找到任务ID: {task_id}")
        except Exception as e:
            test_result.add_step("查询任务ID", "failed", str(e))
            test_result.add_error("查询任务ID", e)
            print(f"\n❌ 查询任务ID失败: {e}")
            print("继续执行后续步骤...")
        
        # 4. 等待任务完成
        print("\n[Step 4] 等待解析任务完成")
        try:
            if not task_id:
                raise Exception("任务ID为空，无法等待")
            
            success = wait_for_task_completion(task_id)
            if success:
                test_result.add_step("等待任务完成", "success", "任务执行成功")
            else:
                test_result.add_step("等待任务完成", "failed", "任务执行失败或超时")
                test_result.add_error("等待任务完成", "任务执行失败")
                print("❌ 任务执行失败")
        except Exception as e:
            test_result.add_step("等待任务完成", "failed", str(e))
            test_result.add_error("等待任务完成", e)
            print(f"❌ 等待任务失败: {e}")
            print("继续执行后续步骤...")
        
        # 5. 获取日志解析结果
        print("\n[Step 5] 获取日志解析结果")
        try:
            if not kb_id:
                raise Exception("知识库ID为空，无法获取解析结果")
            
            result = get_log_parse_results(kb_id)
            
            if "error" in result:
                raise Exception(result["error"])
            
            parse_results = result.get("result", {}).get("log_parse_results", [])
            test_result.log_parse_results = parse_results
            test_result.add_step("获取日志解析结果", "success", f"获取到 {len(parse_results)} 条解析结果", result)
            print(f"✅ 获取解析结果成功: {len(parse_results)} 条")
        except Exception as e:
            test_result.add_step("获取日志解析结果", "failed", str(e))
            test_result.add_error("获取日志解析结果", e)
            print(f"❌ 获取解析结果失败: {e}")
            print("继续执行后续步骤...")
        
        # 6. 获取聚合事件
        print("\n[Step 6] 获取聚合事件")
        try:
            if not kb_id:
                raise Exception("知识库ID为空，无法获取聚合事件")
            
            result = get_aggregated_events(kb_id)
            
            if "error" in result:
                raise Exception(result["error"])
            
            events = result.get("result", {}).get("aggregated_events", [])
            test_result.aggregated_events = events
            test_result.add_step("获取聚合事件", "success", f"获取到 {len(events)} 条聚合事件", result)
            print(f"✅ 获取聚合事件成功: {len(events)} 条")
        except Exception as e:
            test_result.add_step("获取聚合事件", "failed", str(e))
            test_result.add_error("获取聚合事件", e)
            print(f"❌ 获取聚合事件失败: {e}")
        
        # 7. 获取延迟指标（获取全部数据）
        print("\n[Step 7] 获取延迟指标时间曲线数据")
        try:
            result = get_latency_metrics(max_points=-1)  # max_points=-1 获取全部数据
            
            if "error" in result:
                raise Exception(result["error"])
            
            metrics_data = result.get("result", {}).get("metrics", [])
            test_result.latency_metrics = metrics_data
            test_result.add_step("获取延迟指标", "success", f"获取到 {len(metrics_data)} 条延迟指标数据", result)
            print(f"✅ 获取延迟指标成功: {len(metrics_data)} 条")
            
            # 8. 绘制延迟曲线
            print("\n[Step 8] 绘制延迟曲线")
            if metrics_data:
                curve_path = f"latency_curve_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                success = plot_latency_curve(metrics_data, curve_path)
                if success:
                    test_result.add_step("绘制延迟曲线", "success", f"曲线已保存: {curve_path}")
                else:
                    test_result.add_step("绘制延迟曲线", "failed", "曲线绘制失败")
            else:
                print("⚠️  没有延迟指标数据，跳过曲线绘制")
                test_result.add_step("绘制延迟曲线", "pending", "没有数据可绘制")
        except Exception as e:
            test_result.add_step("获取延迟指标", "failed", str(e))
            test_result.add_error("获取延迟指标", e)
            print(f"❌ 获取延迟指标失败: {e}")
        
    finally:
        # 9. 生成 HTML 报告
        print("\n[Step 9] 生成测试报告")
        try:
            generate_html_report(test_result, output_html)
            print(f"✅ 测试报告已生成: {os.path.abspath(output_html)}")
        except Exception as e:
            print(f"❌ 生成报告失败: {e}")
    
    print("\n" + "=" * 70)
    print("全链路测试完成")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())