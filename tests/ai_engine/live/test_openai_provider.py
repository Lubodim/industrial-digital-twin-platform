
from __future__ import annotations

import os
import sys
from pathlib import Path

import django
from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    "config.settings",
)

django.setup()
load_dotenv(PROJECT_ROOT / ".env")


from ai_engine.prompts import build_messages_from_research_package
from ai_engine.providers.openai import OpenAIProvider
from ai_engine.research_package import build_research_package


def main() -> None:
    api_key = os.getenv("OPENAI_API_KEY")
    model = os.getenv("OPENAI_MODEL", "gpt-5-mini")
    timeout_seconds = int(
        os.getenv("OPENAI_TIMEOUT_SECONDS", "90")
    )

    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is missing from the .env file."
        )

    package = build_research_package(
    engineer_question=(
        "Сравни Aluminium 6061 и Aluminium 6082 за CNC фрезована "
        "монтажна конзола. Препоръчай по-подходящия материал, без "
        "да променяш производствената технология. Отговорът да бъде "
        "кратък и всички процентни полета да съдържат само едно число "
        "или null."
    ),
    generic_product_type="CNC machined mounting bracket",
    current_material="Aluminium 6061",
    current_technology="CNC milling",
    batch_size=500,
    current_cycle_time_minutes=35,
    required_properties=[
        "good dimensional accuracy",
        "sufficient mechanical strength",
        "good machinability",
        "corrosion resistance",
    ],
    objective=(
        "Compare Aluminium 6061 and Aluminium 6082 and recommend "
        "the more suitable material"
    ),
)

    messages = build_messages_from_research_package(package)

    provider = OpenAIProvider(
        api_key=api_key,
        model=model,
        timeout_seconds=timeout_seconds,
    )

    result = provider.send_messages(messages)

    print("=" * 70)
    print("PROVIDER INFORMATION")
    print(provider.get_provider_info())

    print("=" * 70)
    print("SUCCESS")
    print(result.success)

    print("=" * 70)
    print("ERROR")
    print(result.error_message or "No error")

    print("=" * 70)
    print("RESPONSE TIME")
    print(result.response_time_ms)

    print("=" * 70)
    print("USAGE")
    print(result.usage)

    print("=" * 70)
    print("STRUCTURED RESPONSE")
    print(result.structured_response)

    if not result.success:
        print("=" * 70)
        print("RAW RESPONSE")
        print(result.raw_response)


if __name__ == "__main__":
    main()