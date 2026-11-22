"""Read-only integration checks without printing credentials or account identifiers."""
import asyncio

import httpx

from app.config import get_settings
from app.materials import MaterialCatalog
from app.services import AIExplainer, ModelUnavailable


async def main() -> int:
    settings = get_settings()
    telegram_ok = False
    webhook_free = False
    async with httpx.AsyncClient(timeout=20) as client:
        try:
            base = f"https://api.telegram.org/bot{settings.bot_token}"
            me = await client.get(f"{base}/getMe")
            hook = await client.get(f"{base}/getWebhookInfo")
            me_data = me.json()
            hook_data = hook.json()
            telegram_ok = bool(me_data.get("ok"))
            webhook_free = bool(hook_data.get("ok")) and not bool(hook_data.get("result", {}).get("url"))
        except Exception:
            pass
    print(f"telegram_credentials_valid={'yes' if telegram_ok else 'no'}")
    print(f"telegram_webhook_free={'yes' if webhook_free else 'no'}")

    model_ok = False
    explainer = AIExplainer(settings.openai_api_key, settings.openai_model)
    try:
        material = MaterialCatalog.load(settings.materials_dir).get("demo-basic-safety")
        result = await explainer.explain(
            material=material,
            user_input="Что делать при сигнале эвакуации?",
            task="Ответь одним коротким предложением по материалу.",
        )
        model_ok = bool(result.explanation and result.source_section)
    except ModelUnavailable as exc:
        print(f"openai_failure={exc}")
    finally:
        await explainer.close()
    print(f"openai_responses_compatible={'yes' if model_ok else 'no'}")
    return 0 if telegram_ok and webhook_free and model_ok else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
