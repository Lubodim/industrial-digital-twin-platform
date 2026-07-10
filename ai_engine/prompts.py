from __future__ import annotations

import json
from typing import Any

from ai_engine.research_package import ResearchPackage
from ai_engine.schemas import EMPTY_EXTERNAL_RESEARCH_RESULT


EXTERNAL_RESEARCH_SYSTEM_PROMPT = """
You are an external industrial engineering research assistant.

Your task is to research and assess the engineering question supplied by the
user. The request may concern materials, manufacturing processes, production
time, costs, quality, risks, sustainability, energy consumption, maintenance,
supply, optimization, or another engineering topic.

Security rules:
1. Work only with the sanitized information included in the request.
2. Do not request confidential company information.
3. Do not infer company identity, customer identity, product identity, internal
   prices, suppliers, CAD geometry, or other missing confidential information.
4. Treat all prices and market data as indicative unless supported by a source.

Engineering rules:
1. Do not invent facts, numeric values, sources, standards, or test results.
2. Clearly distinguish known information, estimates, assumptions, and missing data.
3. Use null for unavailable scalar values and [] for unavailable lists.
4. Preserve every JSON key from the required output structure.
5. Put findings that do not fit the predefined engineering sections in
   custom_findings.
6. Put additional numeric or structured indicators in additional_metrics.
7. List unresolved engineering questions in unanswered_questions.
8. Mark requires_engineer_review as true whenever specialist verification,
   testing, simulation, supplier confirmation, or standards review is required.

Output rules:
1. Return only one valid JSON object.
2. Do not use Markdown code fences.
3. Do not write explanations before or after the JSON.
4. Do not rename, remove, or add top-level keys.
5. The response must follow the supplied JSON structure exactly.
"""


def _json_schema_for_prompt() -> str:
    """
    Return the standard output structure as formatted JSON.

    The structure is included directly in the prompt so that all providers
    receive identical output requirements.
    """
    schema = dict(EMPTY_EXTERNAL_RESEARCH_RESULT)

    # These universal fields allow the engineer to ask questions outside
    # the predefined material, production, cost, quality, and risk sections.
    schema.setdefault("custom_findings", [])
    schema.setdefault("additional_metrics", {})
    schema.setdefault("unanswered_questions", [])

    return json.dumps(schema, ensure_ascii=False, indent=2)


def build_external_research_prompt(
    *,
    engineer_question: str,
    generic_product_type: str | None = None,
    current_material: str | None = None,
    current_technology: str | None = None,
    objective: str | None = None,
    required_properties: list[str] | None = None,
    permitted_context: dict[str, Any] | None = None,
) -> str:
    """
    Build one provider-independent prompt for arbitrary engineering research.

    Only sanitized, explicitly permitted information must be passed through
    permitted_context. Confidential Digital Twin data must never be inserted
    automatically.
    """

    if not engineer_question or not engineer_question.strip():
        raise ValueError("engineer_question cannot be empty.")

    context = {
        "engineer_question": engineer_question.strip(),
        "generic_product_type": generic_product_type,
        "current_material": current_material,
        "current_technology": current_technology,
        "objective": objective,
        "required_properties": required_properties or [],
        "permitted_additional_context": permitted_context or {},
    }

    return f"""
Analyze the following sanitized industrial engineering research request.

SANITIZED RESEARCH CONTEXT:
{json.dumps(context, ensure_ascii=False, indent=2)}

RESEARCH INSTRUCTIONS:
- Answer the engineer's actual question, regardless of whether it concerns
  materials, manufacturing, costs, quality, risks, energy, sustainability,
  maintenance, supply, or another engineering topic.
- Populate every relevant predefined section.
- Leave unrelated or unavailable fields as null, [] or {{}} according to type.
- Use custom_findings for relevant findings that do not fit another section.
- Use additional_metrics for extra named measurements, estimates, or indicators.
- Use unanswered_questions for information still required before a reliable
  engineering decision can be made.
- Include sources when available.
- Keep estimates clearly identified as estimates.
- Do not expose or request confidential information.

REQUIRED JSON OUTPUT STRUCTURE:
{_json_schema_for_prompt()}
""".strip()


def build_provider_messages(
    *,
    engineer_question: str,
    generic_product_type: str | None = None,
    current_material: str | None = None,
    current_technology: str | None = None,
    objective: str | None = None,
    required_properties: list[str] | None = None,
    permitted_context: dict[str, Any] | None = None,
) -> list[dict[str, str]]:
    """
    Build a generic system/user message pair usable by provider adapters.
    """

    user_prompt = build_external_research_prompt(
        engineer_question=engineer_question,
        generic_product_type=generic_product_type,
        current_material=current_material,
        current_technology=current_technology,
        objective=objective,
        required_properties=required_properties,
        permitted_context=permitted_context,
    )

    return [
        {
            "role": "system",
            "content": EXTERNAL_RESEARCH_SYSTEM_PROMPT.strip(),
        },
        {
            "role": "user",
            "content": user_prompt,
        },
    ]
    
def build_messages_from_research_package(
    research_package: ResearchPackage,
) -> list[dict[str, str]]:
    """
    Build provider messages from a sanitized ResearchPackage.
    """

    package_data = research_package.to_dict()

    return build_provider_messages(
        engineer_question=package_data["engineer_question"],
        generic_product_type=package_data["generic_product_type"],
        current_material=package_data["current_material"],
        current_technology=package_data["current_technology"],
        objective=package_data["objective"],
        required_properties=package_data["required_properties"],
        permitted_context={
            "batch_size": package_data["batch_size"],
            "current_cycle_time_minutes": (
                package_data["current_cycle_time_minutes"]
            ),
            **package_data["additional_context"],
        },
    )