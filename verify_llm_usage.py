"""校验最近一次全链路 E2E 评测是否使用了真实 LLM（Agent 端 + Judge 端）。

用法: python verify_llm_usage.py <evaluation_id>
"""
import json
import sys
import urllib.request

BASE = "http://127.0.0.1:9000/api/v1"


def get(path):
    with urllib.request.urlopen(BASE + path) as r:
        return json.load(r)


def main():
    eval_id = sys.argv[1]
    execs = get(f"/evaluations/{eval_id}/executions")["data"]

    for se in execs:
        detail = get(f"/evaluations/{eval_id}/executions/{se['id']}")["data"]
        conv = detail.get("conversation_data") or {}
        tokens = conv.get("total_tokens") or {}
        print("=" * 72)
        print(f"[Agent 端] adapter={detail['agent_adapter_type']} latency={detail['latency_ms']}ms")
        print(f"  tokens: prompt={tokens.get('prompt')} completion={tokens.get('completion')}")
        for m in conv.get("messages", []):
            print(f"  {m['role']}: {m['content'][:90]}")

        results = get(f"/scenario-executions/{se['id']}/judge-results")["data"]["items"]
        for r in results:
            print(f"[Judge:{r['judge_type']}] score={r['overall_score']} verdict={r['overall_verdict']}")
            for ms in r["metric_scores"]:
                reason = (ms.get("reasoning") or "")[:130]
                print(f"    - {ms['metric_key']}={ms['score']} | {reason}")


if __name__ == "__main__":
    main()
