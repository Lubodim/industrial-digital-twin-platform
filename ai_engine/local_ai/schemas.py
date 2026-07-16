"""
JSON schemas used by the local engineering AI.

The schemas define the contract between the local language model
and the application.
"""

from __future__ import annotations

from typing import Any


ENGINEERING_ANALYSIS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "summary",
        "findings",
        "conflicts",
        "missing_information",
        "proposals",
        "overall_confidence_percent",
        "requires_engineer_review",
    ],
    "properties": {
        "summary": {
            "type": "string",
        },
        "findings": {
            "type": "array",
            "items": {
                "type": "string",
            },
        },
        "conflicts": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "topic",
                    "description",
                    "sources",
                ],
                "properties": {
                    "topic": {
                        "type": "string",
                    },
                    "description": {
                        "type": "string",
                    },
                    "sources": {
                        "type": "array",
                        "items": {
                            "type": "string",
                        },
                    },
                },
            },
        },
        "missing_information": {
            "type": "array",
            "items": {
                "type": "string",
            },
        },
        "proposals": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "category",
                    "title",
                    "description",
                    "parameter_name",
                    "current_value",
                    "proposed_value",
                    "unit",
                    "reason",
                    "expected_benefit",
                    "risk_level",
                    "confidence_percent",
                    "requires_validation",
                    "validation_requirements",
                ],
                "properties": {
                    "category": {
                        "type": "string",
                        "enum": [
                            "MATERIAL",
                            "TECHNOLOGY",
                            "GEOMETRY",
                            "COST",
                            "QUALITY",
                            "PRODUCTION",
                            "SAFETY",
                            "OTHER",
                        ],
                    },
                    "title": {
                        "type": "string",
                    },
                    "description": {
                        "type": "string",
                    },
                    "parameter_name": {
                        "type": [
                            "string",
                            "null",
                        ],
                    },
                    "current_value": {
                        "type": [
                            "string",
                            "number",
                            "boolean",
                            "null",
                        ],
                    },
                    "proposed_value": {
                        "type": [
                            "string",
                            "number",
                            "boolean",
                            "null",
                        ],
                    },
                    "unit": {
                        "type": [
                            "string",
                            "null",
                        ],
                    },
                    "reason": {
                        "type": "string",
                    },
                    "expected_benefit": {
                        "type": "string",
                    },
                    "risk_level": {
                        "type": "string",
                        "enum": [
                            "LOW",
                            "MEDIUM",
                            "HIGH",
                            "UNKNOWN",
                        ],
                    },
                    "confidence_percent": {
                        "type": "integer",
                        "minimum": 0,
                        "maximum": 100,
                    },
                    "requires_validation": {
                        "type": "boolean",
                    },
                    "validation_requirements": {
                        "type": "array",
                        "items": {
                            "type": "string",
                        },
                    },
                },
            },
        },
        "overall_confidence_percent": {
            "type": "integer",
            "minimum": 0,
            "maximum": 100,
        },
        "requires_engineer_review": {
            "type": "boolean",
            "const": True,
        },
    },
}