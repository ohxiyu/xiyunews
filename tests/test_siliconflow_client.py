"""SiliconFlow protocol checks; no network calls or real credentials."""
import asyncio
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from src.ai.client import OpenAIClient, create_ai_client
from src.ai.prompts import CONTENT_ANALYSIS_SYSTEM, EVENT_RELATION_SYSTEM, TOPIC_DEDUP_SYSTEM
from src.ai.tokens import reset_usage, task_usage_snapshot
from src.models import AIConfig, AIProvider, AI_PROVIDER_DEFAULTS


def config(**overrides):
    return AIConfig(provider="siliconflow", **{
        **AI_PROVIDER_DEFAULTS[AIProvider.SILICONFLOW], **overrides,
    })


def stub_client(monkeypatch, **options):
    calls, constructors = [], []
    async def create(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(
            usage=SimpleNamespace(prompt_tokens=100, completion_tokens=25,
                completion_tokens_details=SimpleNamespace(reasoning_tokens=10)),
            choices=[SimpleNamespace(finish_reason=options.get("finish_reason", "stop"),
                message=SimpleNamespace(content=options.get("content", '{"ok":true}'),
                    reasoning_content="private reasoning must not be returned"))],
        )
    def factory(**kwargs):
        constructors.append(kwargs)
        return SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    monkeypatch.setenv("SILICONFLOW_API_KEY", "test-only")
    monkeypatch.setattr("src.ai.client.AsyncOpenAI", factory)
    reset_usage()
    client = create_ai_client(config(economy_mode=options.get("economy_mode", True)))
    return client, calls, constructors


def test_factory_uses_siliconflow_key_and_endpoint_without_explicit_url(monkeypatch):
    _, _, constructors = stub_client(monkeypatch)
    client = create_ai_client(config(base_url=None))
    assert isinstance(client, OpenAIClient)
    assert client.model == "Qwen/Qwen3.5-27B"
    assert constructors[-1] == {"api_key": "test-only", "base_url": "https://api.siliconflow.cn/v1",
                                "timeout": 120, "max_retries": 1}


def test_missing_key_never_falls_back_to_old_provider_or_exposes_key(monkeypatch):
    monkeypatch.delenv("SILICONFLOW_API_KEY", raising=False)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "old-provider-only")
    with pytest.raises(ValueError, match="Set SILICONFLOW_API_KEY") as error:
        create_ai_client(config())
    assert "old-provider-only" not in str(error.value)


@pytest.mark.parametrize("system,budget", [(CONTENT_ANALYSIS_SYSTEM, 1536),
                                           (TOPIC_DEDUP_SYSTEM, 1536)])
def test_economy_json_requests_disable_thinking_with_siliconflow_protocol(monkeypatch, system, budget):
    client, calls, _ = stub_client(monkeypatch)
    result = asyncio.run(client.complete(system, "Return JSON"))
    assert result == '{"ok":true}'
    request = calls[0]
    assert request["model"] == "Qwen/Qwen3.5-27B"
    assert request["extra_body"] == {"enable_thinking": False}
    assert request["max_tokens"] == budget
    assert request["response_format"] == {"type": "json_object"}
    assert "reasoning_effort" not in request
    assert "thinking" not in request["extra_body"]


@pytest.mark.parametrize("system,response_format,economy", [
    (EVENT_RELATION_SYSTEM, "json", True),
    ("Write bilingual news analysis", "text", True),
    (CONTENT_ANALYSIS_SYSTEM, "json", False),
])
def test_reasoning_is_bounded_and_text_stays_text(monkeypatch, system, response_format, economy):
    client, calls, _ = stub_client(monkeypatch, economy_mode=economy)
    result = asyncio.run(client.complete(system, "test", max_tokens=8192, response_format=response_format))
    assert result == '{"ok":true}'  # Never return reasoning_content.
    request = calls[0]
    assert request["extra_body"] == {"enable_thinking": True, "thinking_budget": 4096}
    assert request["max_tokens"] == 8192
    assert "reasoning_effort" not in request
    assert ("response_format" in request) == (response_format == "json")


def test_dynamic_scoring_keeps_analysis_budget_and_correct_usage_identity(monkeypatch):
    client, calls, _ = stub_client(monkeypatch)
    before, rest = CONTENT_ANALYSIS_SYSTEM.split("Consider:\n", 1)
    _, calibration = rest.split("Scoring granularity and calibration:", 1)
    system = before + "Fixed edition window\nScoring granularity and calibration:" + calibration
    asyncio.run(client.complete(system, "test"))
    assert calls[0]["max_tokens"] == client.max_tokens
    assert calls[0]["extra_body"]["enable_thinking"] is True
    usage = task_usage_snapshot()[0]
    assert usage["provider"] == "siliconflow"
    assert usage["model"] == "Qwen/Qwen3.5-27B"
    assert usage["stage"] == "content_analysis"
    assert usage["reasoning_tokens"] == 10


@pytest.mark.parametrize("options,error", [({"content": None}, "no usable content"),
                                          ({"finish_reason": "length"}, "truncated")])
def test_reasoning_only_and_truncated_answers_are_rejected(monkeypatch, options, error):
    client, _, _ = stub_client(monkeypatch, **options)
    with pytest.raises(ValueError, match=error):
        asyncio.run(client.complete("Return JSON", "test"))


def test_production_config_and_all_ai_workflow_steps_agree_on_secret():
    root = Path(__file__).parents[1]
    cfg = AIConfig.model_validate(json.loads((root / "data/config.github.json").read_text())["ai"])
    assert cfg.provider == AIProvider.SILICONFLOW
    assert cfg.model == "Qwen/Qwen3.5-27B"
    assert cfg.base_url == "https://api.siliconflow.cn/v1"
    assert cfg.api_key_env == "SILICONFLOW_API_KEY"
    for name, count in [("daily-summary.yml", 2), ("feed-collection.yml", 1), ("x-distribution.yml", 1)]:
        workflow = (root / ".github/workflows" / name).read_text()
        assert workflow.count("SILICONFLOW_API_KEY: ${{ secrets.SILICONFLOW_API_KEY }}") == count
        assert "secrets.DEEPSEEK_API_KEY" not in workflow
