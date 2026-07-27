#!/usr/bin/env python3
"""Phase 6 验收测试: Regression System.

验收标准:
- AC-P6-01: POST 创建回归分析返回完整 scenario_diffs
- AC-P6-02: score_delta = target_score - baseline_score 计算正确
- AC-P6-03: verdict=regressed 当 score_delta < -threshold
- AC-P6-04: verdict=improved 当 score_delta > threshold
- AC-P6-05: verdict=unchanged 当 abs(score_delta) < threshold
- AC-P6-06: 一侧缺失场景时 verdict 正确判定
- AC-P6-07: metric_diffs 包含每个指标的 delta 和 direction
- AC-P6-08: regression_risk 按 regression_rate 正确分级
- AC-P6-09: Dataset 不一致时返回 409
- AC-P6-10: 回放创建的新评测使用同一 Dataset
- AC-P6-11: Diff HTML 报告包含 Top 回归和 Top 改进表
- AC-P6-12: Flaky 检测标记波动大的场景
- AC-P6-13: regression_threshold 参数生效（默认 0.05）
- AC-P6-14: GET 详情返回 scenario_diffs 列表
- AC-P6-15: summary 包含 total_compared/improved/regressed/unchanged/flaky
"""

import asyncio
import sys
import uuid

import httpx

BASE_URL = "http://localhost:9000/api/v1"
RUN_ID = uuid.uuid4().hex[:6]

passed = 0
failed = 0


def check(name: str, condition: bool, detail: str = ""):
    global passed, failed
    if condition:
        passed += 1
        print(f"  ✓ {name}")
    else:
        failed += 1
        print(f"  ✗ {name} {detail}")


async def main():
    global passed, failed

    async with httpx.AsyncClient(base_url=BASE_URL, timeout=60) as client:
        print("=" * 60)
        print("Phase 6 验收测试: Regression System")
        print("=" * 60)

        # ====================================================================
        # 准备: 创建 workspace, project, dataset, scenarios
        # ====================================================================
        print("\n--- 准备测试数据 ---")

        # 创建 workspace
        ws_resp = await client.post("/workspaces", json={
            "name": f"P6-Workspace-{RUN_ID}",
            "slug": f"p6-ws-{RUN_ID}",
        })
        workspace = ws_resp.json().get("data", ws_resp.json())
        workspace_id = workspace["id"]
        check("创建 Workspace", ws_resp.status_code == 201)

        # 创建 project
        proj_resp = await client.post(f"/workspaces/{workspace_id}/projects", json={
            "name": f"P6-Project-{RUN_ID}",
            "slug": f"p6-proj-{RUN_ID}",
            "agent_config": {"adapter_type": "http", "endpoint": "http://localhost:9001"},
        })
        project = proj_resp.json().get("data", proj_resp.json())
        project_id = project["id"]
        check("创建 Project", proj_resp.status_code == 201)

        # 创建 dataset
        ds_resp = await client.post(f"/projects/{project_id}/datasets", json={
            "name": f"P6-Dataset-{RUN_ID}",
            "version": "1.0.0",
        })
        dataset = ds_resp.json().get("data", ds_resp.json())
        dataset_id = dataset["id"]
        check("创建 Dataset", ds_resp.status_code == 201)

        # 创建 scenarios
        scenarios_data = [
            {"external_id": "s1", "title": "基础问答", "input": {"query": "中国的首都是哪里？"}, "expected": {"response_contains": ["北京"]}},
            {"external_id": "s2", "title": "数学运算", "input": {"query": "1+1等于？"}, "expected": {"response_contains": ["2"]}},
            {"external_id": "s3", "title": "语言知识", "input": {"query": "Python是什么？"}, "expected": {"response_contains": ["Python", "编程"]}},
        ]
        sc_resp = await client.post(f"/datasets/{dataset_id}/scenarios/batch", json={"scenarios": scenarios_data})
        check("创建 Scenarios", sc_resp.status_code == 201, f"status={sc_resp.status_code}")

        # ====================================================================
        # 单元测试: ScoreDiffer, RegressionAnalyzer, FlakyDetector
        # ====================================================================
        print("\n--- 单元测试: 核心组件 ---")

        # 导入核心组件
        sys.path.insert(0, "src")
        from agenteval.services.regression.score_differ import ScoreDiffer, ScenarioDiff, RegressionVerdict
        from agenteval.services.regression.regression_analyzer import RegressionAnalyzer
        from agenteval.services.regression.flaky_detector import FlakyDetector
        from agenteval.services.regression.scenario_matcher import ScenarioMatcher

        # AC-P6-02/03/04/05: ScoreDiffer verdict 判定
        differ = ScoreDiffer(regression_threshold=0.05)

        # 模拟场景执行对象
        class MockScenario:
            def __init__(self, external_id, title):
                self.external_id = external_id
                self.title = title

        class MockExec:
            def __init__(self, scenario_id, overall_score, overall_verdict, scenario):
                self.scenario_id = scenario_id
                self.overall_score = overall_score
                self.overall_verdict = overall_verdict
                self.scenario = scenario
                self.judge_results = []

        sid1 = uuid.uuid4()
        scenario1 = MockScenario("s1", "测试场景1")

        # 测试 regressed (delta < -threshold)
        baseline_exec = MockExec(sid1, 0.9, "pass", scenario1)
        target_exec = MockExec(sid1, 0.7, "fail", scenario1)  # delta = -0.2
        pairs = [(baseline_exec, target_exec)]
        diffs = differ.diff(pairs)
        check("AC-P6-03: verdict=regressed 当 delta < -threshold",
              diffs[0].verdict == "regressed",
              f"verdict={diffs[0].verdict}, delta={diffs[0].score_delta}")

        # 测试 improved (delta > threshold)
        baseline_exec2 = MockExec(sid1, 0.6, "fail", scenario1)
        target_exec2 = MockExec(sid1, 0.9, "pass", scenario1)  # delta = +0.3
        pairs2 = [(baseline_exec2, target_exec2)]
        diffs2 = differ.diff(pairs2)
        check("AC-P6-04: verdict=improved 当 delta > threshold",
              diffs2[0].verdict == "improved",
              f"verdict={diffs2[0].verdict}, delta={diffs2[0].score_delta}")

        # 测试 unchanged (abs(delta) < threshold)
        baseline_exec3 = MockExec(sid1, 0.8, "pass", scenario1)
        target_exec3 = MockExec(sid1, 0.82, "pass", scenario1)  # delta = +0.02 < 0.05
        pairs3 = [(baseline_exec3, target_exec3)]
        diffs3 = differ.diff(pairs3)
        check("AC-P6-05: verdict=unchanged 当 abs(delta) < threshold",
              diffs3[0].verdict == "unchanged",
              f"verdict={diffs3[0].verdict}, delta={diffs3[0].score_delta}")

        # AC-P6-02: score_delta 计算
        check("AC-P6-02: score_delta = target - baseline",
              diffs[0].score_delta == -0.2,
              f"delta={diffs[0].score_delta}")

        # AC-P6-06: 一侧缺失场景
        pairs_missing_baseline = [(None, target_exec)]
        diffs_missing_b = differ.diff(pairs_missing_baseline)
        check("AC-P6-06a: baseline 缺失 → improved",
              diffs_missing_b[0].verdict == "improved")

        pairs_missing_target = [(baseline_exec, None)]
        diffs_missing_t = differ.diff(pairs_missing_target)
        check("AC-P6-06b: target 缺失 → regressed",
              diffs_missing_t[0].verdict == "regressed")

        # AC-P6-13: threshold 参数生效
        differ_custom = ScoreDiffer(regression_threshold=0.3)
        baseline_exec4 = MockExec(sid1, 0.8, "pass", scenario1)
        target_exec4 = MockExec(sid1, 0.6, "fail", scenario1)  # delta = -0.2 < 0.3
        pairs4 = [(baseline_exec4, target_exec4)]
        diffs4 = differ_custom.diff(pairs4)
        check("AC-P6-13: threshold=0.3 时 delta=-0.2 → unchanged",
              diffs4[0].verdict == "unchanged",
              f"verdict={diffs4[0].verdict}")

        # AC-P6-08: RegressionAnalyzer 风险分级
        analyzer = RegressionAnalyzer()

        # 构造不同回归率的场景
        def make_diffs(regressed_count, total):
            result = []
            for i in range(total):
                verdict = "regressed" if i < regressed_count else "unchanged"
                result.append(ScenarioDiff(
                    scenario_id=uuid.uuid4(),
                    external_id=f"s{i}",
                    title=f"场景{i}",
                    baseline_score=0.8,
                    target_score=0.6 if verdict == "regressed" else 0.8,
                    score_delta=-0.2 if verdict == "regressed" else 0.0,
                    baseline_verdict="pass",
                    target_verdict="fail" if verdict == "regressed" else "pass",
                    verdict=verdict,
                    metric_deltas={},
                ))
            return result

        # 回归率 25% → critical
        diffs_critical = make_diffs(5, 20)
        analysis_critical = analyzer.analyze(diffs_critical, {})
        check("AC-P6-08a: 回归率 25% → critical",
              analysis_critical.summary["regression_risk"] == "critical",
              f"risk={analysis_critical.summary['regression_risk']}")

        # 回归率 15% → high
        diffs_high = make_diffs(3, 20)
        analysis_high = analyzer.analyze(diffs_high, {})
        check("AC-P6-08b: 回归率 15% → high",
              analysis_high.summary["regression_risk"] == "high",
              f"risk={analysis_high.summary['regression_risk']}")

        # 回归率 5% → medium
        diffs_medium = make_diffs(1, 20)
        analysis_medium = analyzer.analyze(diffs_medium, {})
        check("AC-P6-08c: 回归率 5% → medium",
              analysis_medium.summary["regression_risk"] == "medium",
              f"risk={analysis_medium.summary['regression_risk']}")

        # 回归率 0% → low
        diffs_low = make_diffs(0, 20)
        analysis_low = analyzer.analyze(diffs_low, {})
        check("AC-P6-08d: 回归率 0% → low",
              analysis_low.summary["regression_risk"] == "low",
              f"risk={analysis_low.summary['regression_risk']}")

        # AC-P6-15: summary 包含所有字段
        check("AC-P6-15: summary 包含 total_compared",
              "total_compared" in analysis_low.summary)
        check("AC-P6-15: summary 包含 improved",
              "improved" in analysis_low.summary)
        check("AC-P6-15: summary 包含 regressed",
              "regressed" in analysis_low.summary)
        check("AC-P6-15: summary 包含 unchanged",
              "unchanged" in analysis_low.summary)
        check("AC-P6-15: summary 包含 flaky",
              "flaky" in analysis_low.summary)

        # AC-P6-12: FlakyDetector
        detector = FlakyDetector(threshold_std=0.15)

        class MockExecForFlaky:
            def __init__(self, score):
                self.overall_score = score

        # 波动大的场景 (std > 0.15)
        flaky_history = {
            uuid.uuid4(): [MockExecForFlaky(s) for s in [0.9, 0.3, 0.8, 0.2, 0.9]],  # 高波动
            uuid.uuid4(): [MockExecForFlaky(s) for s in [0.8, 0.82, 0.79, 0.81, 0.8]],  # 低波动
        }
        flaky_ids = detector.detect(flaky_history)
        check("AC-P6-12: FlakyDetector 标记高波动场景",
              len(flaky_ids) == 1,
              f"flaky_count={len(flaky_ids)}")

        # ScenarioMatcher 测试
        matcher = ScenarioMatcher()
        sid_a, sid_b, sid_c = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
        scenario_a = MockScenario("a", "场景A")
        scenario_b = MockScenario("b", "场景B")
        scenario_c = MockScenario("c", "场景C")

        baseline_execs = [
            MockExec(sid_a, 0.8, "pass", scenario_a),
            MockExec(sid_b, 0.7, "pass", scenario_b),
        ]
        target_execs = [
            MockExec(sid_a, 0.9, "pass", scenario_a),
            MockExec(sid_c, 0.6, "fail", scenario_c),  # 新场景
        ]
        matched_pairs = matcher.match(baseline_execs, target_execs)
        check("ScenarioMatcher: 正确匹配场景",
              len(matched_pairs) == 3,
              f"pairs={len(matched_pairs)}")

        # ====================================================================
        # 集成测试: 完整回归分析流程
        # ====================================================================
        print("\n--- 集成测试: API 端到端 ---")

        # 创建两个评测 (使用 mock agent)
        judge_configs = [
            {
                "judge_type": "rule",
                "config": {
                    "metrics": ["correctness"]
                }
            }
        ]

        # 创建 baseline evaluation
        eval1_resp = await client.post(f"/projects/{project_id}/evaluations", json={
            "name": f"Baseline-{RUN_ID}",
            "dataset_id": dataset_id,
            "agent_config": {"adapter_type": "http", "endpoint": "http://localhost:9001"},
            "judge_configs": judge_configs,
            "version_label": "v1.0",
        })
        check("创建 Baseline Evaluation", eval1_resp.status_code in (201, 202))
        baseline_eval_id = eval1_resp.json().get("data", eval1_resp.json())["id"]

        # 创建 target evaluation
        eval2_resp = await client.post(f"/projects/{project_id}/evaluations", json={
            "name": f"Target-{RUN_ID}",
            "dataset_id": dataset_id,
            "agent_config": {"adapter_type": "http", "endpoint": "http://localhost:9001"},
            "judge_configs": judge_configs,
            "version_label": "v2.0",
        })
        check("创建 Target Evaluation", eval2_resp.status_code in (201, 202))
        target_eval_id = eval2_resp.json().get("data", eval2_resp.json())["id"]

        # 等待评测完成
        print("  等待评测完成...")
        for _ in range(60):
            await asyncio.sleep(2)
            e1 = await client.get(f"/evaluations/{baseline_eval_id}")
            e2 = await client.get(f"/evaluations/{target_eval_id}")
            e1_data = e1.json().get("data", e1.json())
            e2_data = e2.json().get("data", e2.json())
            s1, s2 = e1_data["status"], e2_data["status"]
            if s1 in ("completed", "failed") and s2 in ("completed", "failed"):
                break
        else:
            check("评测完成", False, "timeout")
            print(f"\n{'=' * 60}")
            print(f"结果: {passed} passed, {failed} failed")
            return

        check("两个评测都已完成", e1_data["status"] == "completed" and e2_data["status"] == "completed",
              f"status1={e1_data['status']}, status2={e2_data['status']}")

        # AC-P6-01: 创建回归分析
        reg_resp = await client.post(f"/projects/{project_id}/regressions", json={
            "name": f"Regression-{RUN_ID}",
            "baseline_evaluation_id": baseline_eval_id,
            "target_evaluation_id": target_eval_id,
            "regression_threshold": 0.05,
        })
        check("AC-P6-01: POST 创建回归分析", reg_resp.status_code == 201, f"status={reg_resp.status_code}")

        if reg_resp.status_code == 201:
            regression = reg_resp.json()
            regression_id = regression["id"]

            # AC-P6-01: 返回完整 scenario_diffs
            check("AC-P6-01: 返回 scenario_diffs",
                  "scenario_diffs" in regression and len(regression["scenario_diffs"]) > 0,
                  f"diffs_count={len(regression.get('scenario_diffs', []))}")

            # AC-P6-07: metric_diffs 包含 delta 和 direction
            metric_diffs = regression.get("metric_diffs", {})
            if metric_diffs:
                first_metric = list(metric_diffs.values())[0]
                check("AC-P6-07: metric_diffs 包含 delta",
                      "delta" in first_metric)
                check("AC-P6-07: metric_diffs 包含 direction",
                      "direction" in first_metric)
            else:
                check("AC-P6-07: metric_diffs 存在", False, "empty")

            # AC-P6-14: GET 详情返回 scenario_diffs
            detail_resp = await client.get(f"/regressions/{regression_id}")
            check("AC-P6-14: GET 详情返回 scenario_diffs",
                  detail_resp.status_code == 200 and "scenario_diffs" in detail_resp.json())

            # AC-P6-11: Diff HTML 报告
            report_resp = await client.get(f"/regressions/{regression_id}/report?format=html")
            check("AC-P6-11: HTML 报告生成",
                  report_resp.status_code == 200)
            if report_resp.status_code == 200:
                html_content = report_resp.text
                check("AC-P6-11: 报告包含 Top 回归",
                      "Top 回归场景" in html_content)
                check("AC-P6-11: 报告包含 Top 改进",
                      "Top 改进场景" in html_content)

            # JSON 报告
            json_report_resp = await client.get(f"/regressions/{regression_id}/report?format=json")
            check("JSON 报告生成", json_report_resp.status_code == 200)

        # AC-P6-09: Dataset 不一致时返回 409
        # 创建另一个 dataset
        ds2_resp = await client.post(f"/projects/{project_id}/datasets", json={
            "name": f"P6-Dataset2-{RUN_ID}",
            "version": "1.0.0",
        })
        ds2_data = ds2_resp.json().get("data", ds2_resp.json())
        if not ds2_data:
            check("AC-P6-09: 创建第二个 Dataset", False, "failed to create dataset2")
        else:
            dataset2_id = ds2_data["id"]
            # 添加场景到第二个 dataset
            await client.post(f"/datasets/{dataset2_id}/scenarios/batch", json={
                "scenarios": [{"external_id": "s1", "title": "Test", "input": {"query": "Hello"}}]
            })

            # 创建使用不同 dataset 的评测
            eval3_resp = await client.post(f"/projects/{project_id}/evaluations", json={
                "name": f"DiffDataset-{RUN_ID}",
                "dataset_id": dataset2_id,
                "agent_config": {"adapter_type": "http", "endpoint": "http://localhost:9001"},
                "judge_configs": judge_configs,
            })
            eval3_data = eval3_resp.json().get("data", eval3_resp.json())
            if not eval3_data:
                check("AC-P6-09: 创建第三个 Evaluation", False, f"status={eval3_resp.status_code}")
            else:
                diff_dataset_eval_id = eval3_data["id"]

                # 等待完成
                for _ in range(30):
                    await asyncio.sleep(2)
                    e3 = await client.get(f"/evaluations/{diff_dataset_eval_id}")
                    e3_data = e3.json().get("data", e3.json())
                    if e3_data and e3_data["status"] in ("completed", "failed"):
                        break

                # 尝试创建 dataset 不一致的回归分析
                reg_invalid_resp = await client.post(f"/projects/{project_id}/regressions", json={
                    "name": f"InvalidRegression-{RUN_ID}",
                    "baseline_evaluation_id": baseline_eval_id,
                    "target_evaluation_id": diff_dataset_eval_id,
                })
                check("AC-P6-09: Dataset 不一致返回 409",
                      reg_invalid_resp.status_code == 409,
                      f"status={reg_invalid_resp.status_code}")

        # AC-P6-10: Dataset Replay
        replay_resp = await client.post(f"/evaluations/{baseline_eval_id}/replay", json={
            "agent_config": {"adapter_type": "http", "endpoint": "http://localhost:9001"},
            "name": f"Replay-{RUN_ID}",
        })
        check("AC-P6-10: Replay 创建新评测",
              replay_resp.status_code == 201,
              f"status={replay_resp.status_code}")

        if replay_resp.status_code == 201:
            replay_eval_id = replay_resp.json().get("data", replay_resp.json())["evaluation_id"]
            # 验证新评测使用同一 dataset
            replay_eval = await client.get(f"/evaluations/{replay_eval_id}")
            check("AC-P6-10: 回放使用同一 Dataset",
                  replay_eval.json().get("data", replay_eval.json())["dataset_id"] == dataset_id)

        # 列表查询
        list_resp = await client.get(f"/projects/{project_id}/regressions")
        check("列表查询回归分析", list_resp.status_code == 200)

    # ====================================================================
    # 结果汇总
    # ====================================================================
    print("\n" + "=" * 60)
    print(f"Phase 6 验收测试结果: {passed} passed, {failed} failed")
    print("=" * 60)

    if failed == 0:
        print("\n🎉 Phase 6 全部验收通过!")
    else:
        print(f"\n⚠️ 有 {failed} 项未通过")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
