import json

import httpx
import pytest

from app.services.ai_explainer import AIExplainer, ModelUnavailable


@pytest.mark.asyncio
async def test_structured_model_response(material):
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert body["text"]["format"]["type"] == "json_schema"
        return httpx.Response(
            200,
            json={
                "output_text": json.dumps(
                    {
                        "explanation": "Нужно сообщить ответственному.",
                        "source_section": "Сообщение об опасности",
                        "insufficient_material": False,
                        "escalate_to_specialist": False,
                    },
                    ensure_ascii=False,
                )
            },
        )

    service = AIExplainer("test", "gpt-5-mini")
    await service.client.aclose()
    service.client = httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="https://api.openai.com/v1")
    result = await service.explain(material=material, user_input="Что делать?", task="Объясни")
    assert result.insufficient_material is False
    await service.close()


@pytest.mark.asyncio
async def test_api_error_is_sanitized(material):
    service = AIExplainer("secret", "gpt-5-mini")
    await service.client.aclose()
    service.client = httpx.AsyncClient(transport=httpx.MockTransport(lambda _: httpx.Response(500)), base_url="https://api.openai.com/v1")
    with pytest.raises(ModelUnavailable):
        await service.explain(material=material, user_input="test", task="test")
    await service.close()
