from django.test import SimpleTestCase

from ai_engine.validators import validate_external_research_result


class ExternalResearchValidatorTests(SimpleTestCase):
    def test_valid_partial_response_is_normalized(self):
        supplied_data = {
            "schema_version": "1.0",
            "metadata": {
                "provider": "OPENAI",
                "model": "test-model",
                "status": "success",
                "provider_confidence_percent": 85,
            },
            "materials": {
                "recommended_material": "Aluminium 6082",
            },
            "summary": "Alternative material found.",
            "requires_engineer_review": True,
        }

        result = validate_external_research_result(supplied_data)

        self.assertTrue(result.is_valid)
        self.assertEqual(result.errors, [])

        materials = result.normalized_data["materials"]

        self.assertEqual(
            materials["recommended_material"],
            "Aluminium 6082",
        )
        self.assertEqual(materials["alternative_materials"], [])
        self.assertIsNone(materials["comparison_notes"])

    def test_missing_sections_are_added(self):
        supplied_data = {
            "schema_version": "1.0",
            "metadata": {
                "status": "success",
            },
            "requires_engineer_review": True,
        }

        result = validate_external_research_result(supplied_data)

        self.assertTrue(result.is_valid)
        self.assertIn("materials", result.normalized_data)
        self.assertIn("manufacturing", result.normalized_data)
        self.assertIn("costs", result.normalized_data)
        self.assertIn("risks", result.normalized_data)
        self.assertIn("custom_findings", result.normalized_data)
        self.assertIn("additional_metrics", result.normalized_data)
        self.assertIn("unanswered_questions", result.normalized_data)

    def test_unknown_keys_are_ignored_with_warning(self):
        supplied_data = {
            "schema_version": "1.0",
            "metadata": {
                "status": "success",
            },
            "unknown_field": "must not be preserved",
            "requires_engineer_review": True,
        }

        result = validate_external_research_result(supplied_data)

        self.assertTrue(result.is_valid)
        self.assertNotIn("unknown_field", result.normalized_data)
        self.assertIn(
            "Unknown key ignored: unknown_field",
            result.warnings,
        )

    def test_invalid_schema_version_is_rejected(self):
        supplied_data = {
            "schema_version": "2.0",
            "metadata": {
                "status": "success",
            },
            "requires_engineer_review": True,
        }

        result = validate_external_research_result(supplied_data)

        self.assertFalse(result.is_valid)
        self.assertIn(
            "schema_version must be 1.0.",
            result.errors,
        )

    def test_wrong_field_types_are_rejected(self):
        supplied_data = {
            "schema_version": "1.0",
            "metadata": {
                "provider": 123,
                "status": "success",
                "provider_confidence_percent": 150,
            },
            "sources": "not-a-list",
            "requires_engineer_review": "yes",
        }

        result = validate_external_research_result(supplied_data)

        self.assertFalse(result.is_valid)

        combined_errors = "\n".join(result.errors)

        self.assertIn("metadata.provider must be str", combined_errors)
        self.assertIn(
            "metadata.provider_confidence_percent must be between 0 and 100",
            combined_errors,
        )
        self.assertIn("sources must be list", combined_errors)
        self.assertIn(
            "requires_engineer_review must be bool",
            combined_errors,
        )

    def test_non_dictionary_input_is_rejected(self):
        result = validate_external_research_result(
            "not a JSON object"
        )

        self.assertFalse(result.is_valid)
        self.assertEqual(
            result.errors,
            ["External research result must be a JSON object."],
        )