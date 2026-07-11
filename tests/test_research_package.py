from django.test import SimpleTestCase

from ai_engine.research_package import build_research_package


class ResearchPackageTests(SimpleTestCase):
    def test_builds_safe_research_package(self):
        package = build_research_package(
            engineer_question=(
                "Предложи начин за намаляване на производственото време."
            ),
            generic_product_type="CNC machined bracket",
            current_material="Aluminium 6061",
            current_technology="CNC milling",
            batch_size=500,
            current_cycle_time_minutes=35,
            required_properties=[
                "good dimensional accuracy",
                "sufficient mechanical strength",
            ],
            objective="Reduce cycle time",
        )

        data = package.to_dict()

        self.assertEqual(data["batch_size"], 500)
        self.assertEqual(
            data["current_cycle_time_minutes"],
            35.0,
        )
        self.assertEqual(
            data["current_material"],
            "Aluminium 6061",
        )

    def test_removes_confidential_additional_fields(self):
        package = build_research_package(
            engineer_question="Analyze production alternatives.",
            additional_context={
                "batch_size": 1000,
                "current_cycle_time_minutes": 42,
                "company_name": "Confidential Company",
                "customer_name": "Secret Customer",
                "internal_profit_margin": 25,
                "cad_file_path": "secret/product.step",
            },
        )

        context = package.additional_context

        self.assertEqual(context["batch_size"], 1000)
        self.assertEqual(
            context["current_cycle_time_minutes"],
            42.0,
        )

        self.assertNotIn("company_name", context)
        self.assertNotIn("customer_name", context)
        self.assertNotIn("internal_profit_margin", context)
        self.assertNotIn("cad_file_path", context)

    def test_cleans_text_and_list_values(self):
        package = build_research_package(
            engineer_question="  Analyze material alternatives.  ",
            current_material="  Aluminium 6061  ",
            required_properties=[
                "  corrosion resistance  ",
                "",
                "good machinability",
            ],
        )

        self.assertEqual(
            package.engineer_question,
            "Analyze material alternatives.",
        )
        self.assertEqual(
            package.current_material,
            "Aluminium 6061",
        )
        self.assertEqual(
            package.required_properties,
            [
                "corrosion resistance",
                "good machinability",
            ],
        )

    def test_negative_values_are_replaced_with_none(self):
        package = build_research_package(
            engineer_question="Analyze the process.",
            batch_size=-5,
            current_cycle_time_minutes=-10,
        )

        self.assertIsNone(package.batch_size)
        self.assertIsNone(package.current_cycle_time_minutes)

    def test_empty_engineer_question_is_rejected(self):
        with self.assertRaises(ValueError):
            build_research_package(
                engineer_question="   ",
            )