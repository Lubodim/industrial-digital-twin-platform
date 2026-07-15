from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from digital_twins.models import DigitalTwin
from experiments.models import (
    Experiment,
    ExperimentChatMessage,
)


User = get_user_model()


class ExperimentModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="engineer",
            password="test-password",
        )

        self.twin = DigitalTwin.objects.create(
            name="Test Bracket",
            part_number="TEST-BRACKET-001",
            created_by=self.user,
        )

        self.experiment = Experiment.objects.create(
            digital_twin=self.twin,
            name="Weight reduction",
            objective=(
                "Reduce mass without unacceptable loss "
                "of mechanical performance."
            ),
            created_by=self.user,
        )

    def test_experiment_is_linked_to_digital_twin(self):
        self.assertEqual(
            self.experiment.digital_twin,
            self.twin,
        )

        self.assertEqual(
            self.twin.experiments.count(),
            1,
        )

    def test_new_experiment_is_draft(self):
        self.assertEqual(
            self.experiment.status,
            Experiment.Status.DRAFT,
        )

    def test_result_twin_cannot_be_original_twin(self):
        self.experiment.result_twin = self.twin

        with self.assertRaises(ValidationError):
            self.experiment.full_clean()

    def test_twin_created_status_requires_result_twin(self):
        self.experiment.status = (
            Experiment.Status.TWIN_CREATED
        )

        with self.assertRaises(ValidationError):
            self.experiment.full_clean()

    def test_experiment_initially_has_no_messages(self):
        self.assertEqual(
            self.experiment.message_count,
            0,
        )

        self.assertFalse(
            self.experiment.can_request_analysis
        )

    def test_chat_message_sequence_is_automatic(self):
        first_message = (
            ExperimentChatMessage.objects.create(
                experiment=self.experiment,
                role=(
                    ExperimentChatMessage.Role.ENGINEER
                ),
                provider=(
                    ExperimentChatMessage.Provider.NONE
                ),
                content="Can the material be changed?",
                created_by=self.user,
            )
        )

        second_message = (
            ExperimentChatMessage.objects.create(
                experiment=self.experiment,
                role=(
                    ExperimentChatMessage.Role.ASSISTANT
                ),
                provider=(
                    ExperimentChatMessage.Provider.OPENAI
                ),
                content="Yes, after engineering validation.",
                created_by=self.user,
            )
        )

        self.assertEqual(
            first_message.sequence,
            1,
        )

        self.assertEqual(
            second_message.sequence,
            2,
        )

    def test_engineer_message_cannot_have_ai_provider(self):
        message = ExperimentChatMessage(
            experiment=self.experiment,
            role=ExperimentChatMessage.Role.ENGINEER,
            provider=(
                ExperimentChatMessage.Provider.OPENAI
            ),
            content="Invalid message.",
            created_by=self.user,
        )

        with self.assertRaises(ValidationError):
            message.full_clean()

    def test_assistant_message_requires_provider(self):
        message = ExperimentChatMessage(
            experiment=self.experiment,
            role=ExperimentChatMessage.Role.ASSISTANT,
            provider=(
                ExperimentChatMessage.Provider.NONE
            ),
            content="Invalid assistant response.",
        )

        with self.assertRaises(ValidationError):
            message.full_clean()

    def test_empty_message_is_rejected(self):
        message = ExperimentChatMessage(
            experiment=self.experiment,
            role=ExperimentChatMessage.Role.ENGINEER,
            provider=(
                ExperimentChatMessage.Provider.NONE
            ),
            content="   ",
            created_by=self.user,
        )

        with self.assertRaises(ValidationError):
            message.full_clean()

    def test_analysis_requires_question_and_external_answer(
        self,
    ):
        ExperimentChatMessage.objects.create(
            experiment=self.experiment,
            role=ExperimentChatMessage.Role.ENGINEER,
            provider=ExperimentChatMessage.Provider.NONE,
            content="Can we reduce the weight?",
            created_by=self.user,
        )

        self.assertFalse(
            self.experiment.can_request_analysis
        )

        ExperimentChatMessage.objects.create(
            experiment=self.experiment,
            role=ExperimentChatMessage.Role.ASSISTANT,
            provider=ExperimentChatMessage.Provider.OPENAI,
            content="A material or geometry change may help.",
        )

        self.assertTrue(
            self.experiment.can_request_analysis
        )

    def test_message_count_properties(self):
        ExperimentChatMessage.objects.create(
            experiment=self.experiment,
            role=ExperimentChatMessage.Role.ENGINEER,
            provider=ExperimentChatMessage.Provider.NONE,
            content="Question one.",
            created_by=self.user,
        )

        ExperimentChatMessage.objects.create(
            experiment=self.experiment,
            role=ExperimentChatMessage.Role.ASSISTANT,
            provider=ExperimentChatMessage.Provider.OPENAI,
            content="Answer one.",
        )

        self.assertEqual(
            self.experiment.message_count,
            2,
        )

        self.assertEqual(
            self.experiment.engineer_message_count,
            1,
        )