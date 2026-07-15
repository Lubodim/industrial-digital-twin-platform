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


from ai_engine.orchestrator import run_external_research
from ai_engine.research_package import build_research_package


def main() -> None:
    package = build_research_package(
        engineer_question=(
            "Предложи две практични възможности за намаляване "
            "на времето за CNC обработка, без промяна на материала."
        ),
        generic_product_type="CNC machined mounting bracket",
        current_material="Aluminium 6061",
        current_technology="CNC milling",
        batch_size=500,
        current_cycle_time_minutes=35,
        required_properties=[
            "good dimensional accuracy",
            "sufficient mechanical strength",
        ],
        objective="Reduce CNC cycle time",
    )

    result = run_external_research(
        research_package=package,
        provider_name="openai",
    )

    print("=" * 70)
    print("ORCHESTRATION SUCCESS")
    print(result.success)

    print("=" * 70)
    print("PROVIDER")
    print(result.provider_name)

    print("=" * 70)
    print("ERROR")
    print(result.error_message or "No error")

    print("=" * 70)
    print("METADATA")
    print(result.metadata)

    print("=" * 70)
    print("STRUCTURED RESPONSE")
    print(result.structured_response)


if __name__ == "__main__":
    main()