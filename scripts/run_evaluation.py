#!/usr/bin/env python
"""电商 Agent 评测运行脚本

用法：
  python scripts/run_evaluation.py                    # 跑全部 200 条
  python scripts/run_evaluation.py --limit 20         # 只跑前 20 条
  python scripts/run_evaluation.py --category order   # 只跑订单类
"""
import argparse
import json
import os
import subprocess
import sys
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import httpx

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MOCK_PORT = 9099
AGENT_PORT = 8099


def start_services():
    """启动 mock server 和 agent API"""
    print("启动 mock server...")
    mock_log = open(PROJECT_ROOT / "reports" / "_mock.log", "w")
    mock_proc = subprocess.Popen(
        [sys.executable, "-c", f"""
import sys
sys.path.insert(0, r'{PROJECT_ROOT}')
import uvicorn
from scripts.mock_server import app
uvicorn.run(app, host='127.0.0.1', port={MOCK_PORT})
"""],
        stdout=mock_log,
        stderr=mock_log,
    )

    print("启动 agent API...")
    agent_log = open(PROJECT_ROOT / "reports" / "_agent.log", "w")
    env = dict(os.environ)
    env["ECOMMERCE_API_URL"] = f"http://127.0.0.1:{MOCK_PORT}"
    env["AUTH_ENABLED"] = "false"
    agent_proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "src.api.main:app",
         "--port", str(AGENT_PORT), "--host", "127.0.0.1"],
        cwd=str(PROJECT_ROOT),
        stdout=agent_log,
        stderr=agent_log,
        env=env,
    )

    print("等待服务启动...")
    for i in range(60):
        try:
            r = httpx.get(f"http://127.0.0.1:{AGENT_PORT}/health/", timeout=2)
            if r.status_code == 200:
                print(f"服务已就绪（耗时 {i+1}s）")
                return mock_proc, agent_proc
        except (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadTimeout):
            pass
        time.sleep(1)

    mock_proc.terminate()
    agent_proc.terminate()
    print(f"\n=== mock log (last 800 chars) ===")
    try:
        print(open(PROJECT_ROOT / "reports" / "_mock.log").read()[-800:])
    except Exception:
        pass
    print(f"\n=== agent log (last 800 chars) ===")
    try:
        print(open(PROJECT_ROOT / "reports" / "_agent.log").read()[-800:])
    except Exception:
        pass
    raise RuntimeError("服务启动超时")


def run_test_case(case: dict, client: httpx.Client) -> dict:
    """运行单条测试用例"""
    start_time = time.time()
    try:
        r = client.post(
            f"http://127.0.0.1:{AGENT_PORT}/api/v1/chat/",
            json={
                "session_id": f"eval_{case['id']}",
                "user_id": "eval_user",
                "message": case["user_input"],
                "context": case.get("context", {})
            },
            timeout=60.0
        )
        duration_ms = (time.time() - start_time) * 1000

        if r.status_code != 200:
            return {
                "id": case["id"],
                "success": False,
                "error": f"HTTP {r.status_code}",
                "duration_ms": duration_ms
            }

        data = r.json()
        response_text = data.get("message", "")
        tool_calls = data.get("tool_calls", [])
        called_tools = [tc["tool"] for tc in tool_calls]

        # 判断成功：success=True + 期望工具都被调用 + 关键词都在回复里
        tools_match = all(t in called_tools for t in case["expected_tools"])
        keywords_match = all(kw in response_text for kw in case["expected_response_keywords"])

        passed = data.get("success", False) and tools_match and keywords_match

        return {
            "id": case["id"],
            "success": passed,
            "response": response_text[:200],
            "called_tools": called_tools,
            "expected_tools": case["expected_tools"],
            "duration_ms": duration_ms,
            "tools_match": tools_match,
            "keywords_match": keywords_match
        }
    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        return {
            "id": case["id"],
            "success": False,
            "error": str(e),
            "duration_ms": duration_ms
        }


def calculate_metrics(results: list, test_cases: list) -> dict:
    """计算评测指标"""
    total = len(results)
    passed = sum(1 for r in results if r["success"])

    durations = [r["duration_ms"] for r in results if "duration_ms" in r]
    durations.sort()

    by_category = defaultdict(lambda: {"total": 0, "passed": 0})
    for r in results:
        case = next(c for c in test_cases if c["id"] == r["id"])
        cat = case["category"]
        by_category[cat]["total"] += 1
        if r["success"]:
            by_category[cat]["passed"] += 1

    tool_call_correct = sum(1 for r in results if r.get("tools_match", False))

    return {
        "total": total,
        "passed": passed,
        "accuracy": passed / total if total > 0 else 0,
        "task_completion_rate": passed / total if total > 0 else 0,
        "tool_call_accuracy": tool_call_correct / total if total > 0 else 0,
        "avg_response_time_ms": sum(durations) / len(durations) if durations else 0,
        "p95_response_time_ms": durations[int(len(durations) * 0.95)] if durations else 0,
        "p99_response_time_ms": durations[int(len(durations) * 0.99)] if durations else 0,
        "by_category": dict(by_category)
    }


def generate_report(metrics: dict, results: list, test_cases: list, output_dir: Path):
    """生成评测报告"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # JSON 报告
    json_path = output_dir / f"eval_report_{timestamp}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({
            "timestamp": timestamp,
            "metrics": metrics,
            "results": results
        }, f, ensure_ascii=False, indent=2)

    # Markdown 报告
    md_path = output_dir / f"eval_report_{timestamp}.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(f"# 电商 Agent 评测报告\n\n")
        f.write(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  \n")
        f.write(f"**测试用例数**: {metrics['total']}  \n\n")

        f.write("## 总体指标\n\n")
        f.write("| 指标 | 值 |\n")
        f.write("|------|----|\n")
        f.write(f"| 准确率 | {metrics['accuracy']:.2%} ({metrics['passed']}/{metrics['total']}) |\n")
        f.write(f"| 任务完成率 | {metrics['task_completion_rate']:.2%} |\n")
        f.write(f"| 工具调用准确率 | {metrics['tool_call_accuracy']:.2%} |\n")
        f.write(f"| 平均响应时间 | {metrics['avg_response_time_ms']:.0f} ms |\n")
        f.write(f"| P95 响应时间 | {metrics['p95_response_time_ms']:.0f} ms |\n")
        f.write(f"| P99 响应时间 | {metrics['p99_response_time_ms']:.0f} ms |\n\n")

        f.write("## 分类指标\n\n")
        f.write("| 分类 | 准确率 | 通过/总数 |\n")
        f.write("|------|--------|----------|\n")
        for cat, stats in metrics["by_category"].items():
            acc = stats["passed"] / stats["total"] if stats["total"] > 0 else 0
            f.write(f"| {cat} | {acc:.2%} | {stats['passed']}/{stats['total']} |\n")

        f.write("\n## 失败案例（前 10 条）\n\n")
        failed = [r for r in results if not r["success"]][:10]
        for r in failed:
            case = next(c for c in test_cases if c["id"] == r["id"])
            f.write(f"### {r['id']} - {case['user_input']}\n\n")
            f.write(f"- **期望工具**: {case['expected_tools']}\n")
            f.write(f"- **实际调用**: {r.get('called_tools', [])}\n")
            f.write(f"- **错误**: {r.get('error', 'N/A')}\n\n")

        f.write("## 优化建议\n\n")
        if metrics["accuracy"] < 0.85:
            f.write("- 准确率低于 85%，建议优化 prompt 或增加工具描述清晰度\n")
        if metrics["tool_call_accuracy"] < 0.90:
            f.write("- 工具调用准确率低于 90%，检查工具名称和参数定义\n")
        if metrics["p95_response_time_ms"] > 5000:
            f.write("- P95 响应时间超过 5s，考虑优化工具调用链或启用缓存\n")

    print(f"\n报告已生成:")
    print(f"  JSON: {json_path}")
    print(f"  Markdown: {md_path}")


def main():
    parser = argparse.ArgumentParser(description="电商 Agent 评测运行器")
    parser.add_argument("--dataset", default="tests/evaluation/test_cases/ecommerce_cases.json",
                        help="数据集路径")
    parser.add_argument("--limit", type=int, help="只跑前 N 条")
    parser.add_argument("--category", help="只跑某个分类")
    args = parser.parse_args()

    # 加载数据集
    dataset_path = PROJECT_ROOT / args.dataset
    with open(dataset_path, encoding="utf-8") as f:
        dataset = json.load(f)

    test_cases = dataset["test_cases"]
    if args.category:
        test_cases = [c for c in test_cases if c["category"] == args.category]
    if args.limit:
        test_cases = test_cases[:args.limit]

    print(f"加载 {len(test_cases)} 条测试用例")

    # 启动服务
    mock_proc, agent_proc = start_services()

    try:
        # 运行评测
        results = []
        client = httpx.Client()
        for i, case in enumerate(test_cases, 1):
            print(f"[{i}/{len(test_cases)}] {case['id']}: {case['user_input'][:30]}...", end=" ")
            result = run_test_case(case, client)
            results.append(result)
            status = "PASS" if result["success"] else "FAIL"
            print(f"{status} ({result.get('duration_ms', 0):.0f}ms)")

        # 计算指标
        metrics = calculate_metrics(results, test_cases)

        # 生成报告
        output_dir = PROJECT_ROOT / "reports"
        output_dir.mkdir(exist_ok=True)
        generate_report(metrics, results, test_cases, output_dir)

        # 打印摘要
        print(f"\n=== 评测完成 ===")
        print(f"准确率: {metrics['accuracy']:.2%}")
        print(f"工具调用准确率: {metrics['tool_call_accuracy']:.2%}")
        print(f"平均响应时间: {metrics['avg_response_time_ms']:.0f} ms")

    finally:
        print("\n关闭服务...")
        mock_proc.terminate()
        agent_proc.terminate()
        mock_proc.wait(timeout=5)
        agent_proc.wait(timeout=5)


if __name__ == "__main__":
    main()
