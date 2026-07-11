from django.test import SimpleTestCase

from ai_engine.prompts import build_messages_from_research_package
from ai_engine.research_package import build_research_package


class PromptBuilderTests(SimpleTestCase):
    def test_builds_system_and_user_messages(self):
        package = build_research_package(
            engineer_question=(
                "Намали времето за производство, без да променяш материала."
            ),
            generic_product_type="Machined bracket",
            current_material="Aluminium 6061",
            current_technology="CNC milling",
            batch_size=500,
        )

        messages = build_messages_from_research_package(package)

        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[0]["role"], "system")
        self.assertEqual(messages[1]["role"], "user")

    def test_prompt_contains_engineer_question(self):
        question = "Предложи технология с по-нисък енергиен разход."

        package = build_research_package(
            engineer_question=question,
            generic_product_type="Industrial bracket",
        )

        messages = build_messages_from_research_package(package)

        self.assertIn(question, messages[1]["content"])

    def test_prompt_contains_required_json_keys(self):
        package = build_research_package(
            engineer_question="Analyze alternatives.",
        )

        messages = build_messages_from_research_package(package)
        user_prompt = messages[1]["content"]

        self.assertIn('"schema_version"', user_prompt)
        self.assertIn('"materials"', user_prompt)
        self.assertIn('"manufacturing"', user_prompt)
        self.assertIn('"costs"', user_prompt)
        self.assertIn('"custom_findings"', user_prompt)
        self.assertIn('"additional_metrics"', user_prompt)
        self.assertIn('"unanswered_questions"', user_prompt)

    def test_prompt_does_not_include_filtered_confidential_fields(self):
        package = build_research_package(
            engineer_question="Analyze process optimization.",
            additional_context={
                "batch_size": 250,
                "company_name": "Confidential Company",
                "internal_profit_margin": 30,
            },
        )

        messages = build_messages_from_research_package(package)
        user_prompt = messages[1]["content"]

        self.assertIn('"batch_size": 250', user_prompt)
        self.assertNotIn("Confidential Company", user_prompt)
        self.assertNotIn("internal_profit_margin", user_prompt)