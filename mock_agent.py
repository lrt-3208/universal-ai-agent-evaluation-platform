"""Mock HTTP Agent server for acceptance testing.
Listens on port 9001. Uses real LLM (qwen) if available, else echoes.
"""

import os
import time

from fastapi import FastAPI
from fastapi.responses import JSONResponse

mock_app = FastAPI(title="MockAgent")

# Try to use real LLM for responses
_llm_client = None


def _get_llm_client():
    global _llm_client
    if _llm_client is None:
        try:
            import openai
            api_key = os.environ.get("LLM_API_KEY", "")
            base_url = os.environ.get("LLM_BASE_URL", "")
            if api_key and base_url:
                _llm_client = openai.AsyncOpenAI(api_key=api_key, base_url=base_url)
        except Exception:
            pass
    return _llm_client


@mock_app.post("/chat")
async def mock_chat(request_body: dict):
    """Agent endpoint: uses real LLM if configured, else mock."""
    messages = request_body.get("messages", [])
    user_msg = ""
    if messages:
        for m in reversed(messages):
            if m.get("role") == "user":
                user_msg = m.get("content", "")
                break

    model_name = os.environ.get("LLM_DEFAULT_MODEL", "mock-agent-v1")
    client = _get_llm_client()

    if client:
        # Real LLM response
        try:
            completion = await client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": "你是一个智能助手，请简洁准确地回答用户问题。"},
                    {"role": "user", "content": user_msg},
                ],
                temperature=0.7,
                max_tokens=512,
            )
            choice = completion.choices[0]
            usage = completion.usage
            response_text = choice.message.content or ""
            return JSONResponse({
                "messages": [{"role": "assistant", "content": response_text}],
                "response": response_text,
                "tool_calls": [],
                "tokens": {
                    "prompt": usage.prompt_tokens if usage else 0,
                    "completion": usage.completion_tokens if usage else 0,
                },
                "model": completion.model,
                "finish_reason": choice.finish_reason or "stop",
                "cost_usd": 0.0,
            })
        except Exception as e:
            # Fallback to mock on error
            response_text = f"Mock response to: {user_msg[:50]} (LLM error: {str(e)[:30]})"
    else:
        # Mock response
        time.sleep(0.05)
        response_text = f"Mock response to: {user_msg[:50]}"

    return JSONResponse({
        "messages": [{"role": "assistant", "content": response_text}],
        "response": response_text,
        "tool_calls": [],
        "tokens": {"prompt": 10, "completion": 20},
        "model": "mock-agent-v1",
        "finish_reason": "stop",
        "cost_usd": 0.001,
    })


if __name__ == "__main__":
    import uvicorn
    # Load .env for LLM config
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
    uvicorn.run(mock_app, host="0.0.0.0", port=9001)
