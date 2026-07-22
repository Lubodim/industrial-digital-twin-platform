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


from ai_engine.external_research_agent import (
    ExternalResearchAgent,
)
from ai_engine.research_package import (
    build_research_package,
)


def main() -> None:
    package = build_research_package(
        engineer_question=(
            "Предложи две практични възможности "
            "за намаляване на CNC обработката, "
            "без промяна на материала."
        ),
        generic_product_type=(
            "CNC machined mounting bracket"
        ),
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

    agent = ExternalResearchAgent()

    result = agent.run(
        research_package=package,
        provider_names=["openai"],
    )

    print("=" * 70)
    print("RUN ID")
    print(result.run_id)

    print("=" * 70)
    print("SUCCESS")
    print(result.success)

    print("=" * 70)
    print("SUCCESSFUL PROVIDERS")
    print(result.successful_providers)

    print("=" * 70)
    print("FAILED PROVIDERS")
    print(result.failed_providers)

    for record in result.provider_records:
        print("=" * 70)
        print("PROVIDER")
        print(record.provider_name)

        print("SUCCESS")
        print(record.success)

        print("RAW FILE")
        print(record.raw_file_path)

        print("VALIDATED FILE")
        print(record.validated_file_path)

        print("ERROR")
        print(record.error_message or "No error")


if __name__ == "__main__":
    main()