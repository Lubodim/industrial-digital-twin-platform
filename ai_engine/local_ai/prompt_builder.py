"""
Builder for local engineering analysis prompts.

The builder converts already prepared Python data structures into
deterministic JSON sections for the local language model.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from ai_engine.local_ai.prompts.engineering_analysis import (
    ENGINEERING_ANALYSIS_SYSTEM_PROMPT,
    ENGINEERING_ANALYSIS_USER_TEMPLATE,
)
from ai_engine.local_ai.schemas import (
    ENGINEERING_ANALYSIS_SCHEMA,
)


@dataclass(frozen=True, slots=True)
class BuiltEngineeringPrompt:
    """
    Complete prompt package ready for OllamaClient.ask().
    """

    system_prompt: str
    user_prompt: str
    response_schema: dict[str, Any]


class EngineeringPromptBuilder:
    """
    Build the local engineering-analysis prompt.

    This class receives plain Python structures. It does not read
    Django models or query the database.
    """

    def build(
        self,
        *,
        digital_twin: Mapping[str, Any],
        experiment: Mapping[str, Any],
        chat_history: Sequence[Mapping[str, Any]],
        external_research: Mapping[str, Any],
        materials: Sequence[Mapping[str, Any]] | None = None,
        technologies: Sequence[Mapping[str, Any]] | None = None,
        previous_experiments: (
            Sequence[Mapping[str, Any]] | None
        ) = None,
    ) -> BuiltEngineeringPrompt:
        """
        Build a deterministic engineering prompt package.
        """

        user_prompt = (
            ENGINEERING_ANALYSIS_USER_TEMPLATE.format(
                digital_twin_json=self._to_json(
                    digital_twin
                ),
                experiment_json=self._to_json(
                    experiment
                ),
                chat_history_json=self._to_json(
                    list(chat_history)
                ),
                external_research_json=self._to_json(
                    external_research
                ),
                materials_json=self._to_json(
                    list(materials or [])
                ),
                technologies_json=self._to_json(
                    list(technologies or [])
                ),
                previous_experiments_json=self._to_json(
                    list(
                        previous_experiments
                        or []
                    )
                ),
                response_schema_json=self._to_json(
                    ENGINEERING_ANALYSIS_SCHEMA
                ),
            )
        )

        return BuiltEngineeringPrompt(
            system_prompt=(
                ENGINEERING_ANALYSIS_SYSTEM_PROMPT
            ),
            user_prompt=user_prompt,
            response_schema=dict(
                ENGINEERING_ANALYSIS_SCHEMA
            ),
        )

    @staticmethod
    def _to_json(
        value: Any,
    ) -> str:
        """
        Serialize prompt data consistently and readably.
        """

        return json.dumps(
            value,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
            default=str,
        )
