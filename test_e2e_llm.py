#!/usr/bin/env python3
"""End-to-End Evaluation Test with Real LLM Judge

Flow:
1. Create workspace/project/dataset (2 scenarios)
2. Create evaluation with LLM Judge config
3. Wait for execution + scoring
4. Verify LLM Judge produced real scores
5. Generate report
"""

import asyncio
import sys
import time
import uuid as uuid_mod

import httpx

BASE = "http://localhost:9000/api/v1"
RUN_ID = uuid_mod.uuid4().hex[:6]


async def main():
    print("=" * 60)
    print("E2E Evaluation with Real LLM Judge (qwen3.7-plus)")
    print("=" * 60)

    async with httpx.AsyncClient(timeout=60.0) as c:
        # 1. Create workspace
        print("\n--- Step 1: Setup workspace/project/dataset ---")
        r = await c.post(f"{BASE}/workspaces", json={"name": "E2E LLM Test", "slug": f"e2e-llm-{RUN_ID}", "description": "E2E test"})
        ws_id = r.json()["data"]["id"]
        print(f"  Workspace: {ws_id}")

        # 2. Create project
        r = await c.post(f"{BASE}/workspaces/{ws_id}/projects", json={
            "name": "LLM Judge E2E",
            "slug": f"llm-judge-{RUN_ID}",
            "description": "test",
            "agent_config": {
                "adapter_type": "http",
                "endpoint": "http://localhost:9001",
            },
        })
        proj_id = r.json()["data"]["id"]
        print(f"  Project: {proj_id}")

        # 3. Create dataset
        r = await c.post(f"{BASE}/projects/{proj_id}/datasets", json={
            "name": "E2E Dataset",
            "version": "1.0.0",
        })
        ds_id = r.json()["data"]["id"]
        print(f"  Dataset: {ds_id}")

        # 4. Batch create scenarios
        r = await c.post(f"{BASE}/datasets/{ds_id}/scenarios/batch", json={
            "scenarios": [
                {
                    "external_id": "e2e-001",
                    "title": "中国首都",
                    "input": {"user_message": "中国的首都是哪里？"},
                    "expected": {
                        "reference_answer": "中国的首都是北京。",
                        "response_contains": ["北京"],
                    },
                    "tags": ["geography"],
                },
                {
                    "external_id": "e2e-002",
                    "title": "数学运算",
                    "input": {"user_message": "1+1等于几？"},
                    "expected": {
                        "reference_answer": "1+1等于2。",
                        "response_contains": ["2"],
                    },
                    "tags": ["math"],
                },
            ],
        })
        assert r.status_code == 201, f"Scenario creation failed: {r.text}"
        print(f"  Scenarios: 2 created")

        # 4. Create evaluation with BOTH rule + LLM judge
        print("\n--- Step 2: Create evaluation (Rule + LLM Judge) ---")
        r = await c.post(f"{BASE}/projects/{proj_id}/evaluations", json={
            "name": "E2E LLM Judge Test",
            "dataset_id": ds_id,
            "agent_config": {
                "adapter_type": "http",
                "endpoint": "http://localhost:9001",
            },
            "judge_configs": [
                {
                    "judge_type": "rule",
                    "metrics": ["correctness"],
                },
                {
                    "judge_type": "llm",
                    "metrics": ["correctness", "coherence", "helpfulness"],
                },
            ],
            "config": {
                "auto_judge": True,
            },
        })
        assert r.status_code == 202, f"Expected 202, got {r.status_code}: {r.text}"
        eval_id = r.json()["data"]["id"]
        print(f"  Evaluation: {eval_id}")
        print(f"  Judges: Rule(correctness) + LLM(correctness, coherence, helpfulness)")

        # 5. Wait for completion
        print("\n--- Step 3: Waiting for execution + LLM Judge scoring ---")
        for i in range(60):
            await asyncio.sleep(2)
            r = await c.get(f"{BASE}/evaluations/{eval_id}")
            status = r.json()["data"]["status"]
            if i % 5 == 0:
                print(f"  [{i*2}s] Status: {status}")
            if status in ("completed", "failed"):
                break

        print(f"  Final status: {status}")
        if status != "completed":
            print("  ERROR: Evaluation did not complete!")
            return 1

        # 6. Check judge results
        print("\n--- Step 4: Verify LLM Judge Results ---")
        r = await c.get(f"{BASE}/evaluations/{eval_id}/executions")
        executions = r.json()["data"]
        print(f"  Executions: {len(executions)}")

        for ex in executions:
            scenario_id = ex["scenario_id"]
            score = ex.get("overall_score")
            verdict = ex.get("overall_verdict")
            print(f"  Scenario {ex.get('id', '')[:8]}... score={score}, verdict={verdict}")

        # Get judge results for first execution
        if executions:
            exec_id = executions[0]["id"]
            r = await c.get(f"{BASE}/scenario-executions/{exec_id}/judge-results")
            if r.status_code == 200:
                judge_data = r.json().get("data", {})
                judge_results = judge_data.get("items", [])
                print(f"\n  Judge Results for execution {exec_id[:8]}...:")
                for jr in judge_results:
                    print(f"    [{jr['judge_type']}] score={jr.get('overall_score')}, verdict={jr.get('overall_verdict')}")
                    for ms in jr.get("metric_scores", []):
                        reasoning = ms.get('reasoning', '') or ''
                        print(f"      - {ms['metric_key']}: {ms['score']:.2f} ({reasoning[:60]})")

        # 7. Generate report
        print("\n--- Step 5: Generate HTML Report ---")
        r = await c.post(f"{BASE}/evaluations/{eval_id}/reports", json={"format": "html"})
        assert r.status_code == 202
        report_id = r.json()["data"]["id"]
        print(f"  Report: {report_id}")

        # Wait for report
        for _ in range(10):
            await asyncio.sleep(1)
            r = await c.get(f"{BASE}/reports/{report_id}")
            if r.json()["data"]["status"] == "completed":
                break

        report = r.json()["data"]
        print(f"  Report status: {report['status']}")
        if report.get("summary"):
            s = report["summary"]
            print(f"  Summary: pass_rate={s.get('pass_rate', 0):.1%}, findings={s.get('key_findings', [])}")

        print("\n" + "=" * 60)
        print("E2E TEST PASSED - Full pipeline with real LLM Judge works!")
        print("=" * 60)
        return 0


if __name__ == "__main__":
    code = asyncio.run(main())
    sys.exit(code)
