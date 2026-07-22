from django.test import SimpleTestCase

from ai_engine.parsers.json_parser import parse_json_response


class JSONParserTests(SimpleTestCase):
    def test_parses_plain_json_object(self):
        response = '{"summary": "Valid response"}'

        result = parse_json_response(response)

        self.assertTrue(result.success)
        self.assertEqual(result.data["summary"], "Valid response")
        self.assertEqual(result.error_message, "")

    def test_parses_json_inside_markdown_fence(self):
        response = (
            "```json\n"
            "{\n"
            '  "summary": "Wrapped response",\n'
            '  "requires_engineer_review": true\n'
            "}\n"
            "```"
        )

        result = parse_json_response(response)

        self.assertTrue(result.success)
        self.assertEqual(result.data["summary"], "Wrapped response")
        self.assertTrue(result.data["requires_engineer_review"])

    def test_extracts_json_from_surrounding_text(self):
        response = (
            "Here is the requested result:\n\n"
            "{\n"
            '  "summary": "Extracted response",\n'
            '  "materials": {\n'
            '    "recommended_material": "Aluminium 6082"\n'
            "  }\n"
            "}\n\n"
            "End of response."
        )

        result = parse_json_response(response)

        self.assertTrue(result.success)
        self.assertEqual(result.data["summary"], "Extracted response")
        self.assertEqual(
            result.data["materials"]["recommended_material"],
            "Aluminium 6082",
        )

    def test_rejects_invalid_json(self):
        response = (
            "{\n"
            '  "summary": "Broken response",\n'
            "}"
        )

        result = parse_json_response(response)

        self.assertFalse(result.success)
        self.assertIn("Invalid JSON", result.error_message)

    def test_rejects_json_array(self):
        response = '["not", "an", "object"]'

        result = parse_json_response(response)

        self.assertFalse(result.success)
        self.assertEqual(
            result.error_message,
            "The top-level JSON value must be an object.",
        )

    def test_rejects_empty_response(self):
        result = parse_json_response("   ")

        self.assertFalse(result.success)
        self.assertEqual(result.error_message, "AI response is empty.")

    def test_rejects_non_string_response(self):
        result = parse_json_response({"summary": "Invalid input type"})

        self.assertFalse(result.success)
        self.assertEqual(
            result.error_message,
            "AI response must be a string.",
        )