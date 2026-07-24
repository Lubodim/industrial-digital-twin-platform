from django.contrib.auth import get_user_model
from django.test import TestCase

from conversation.enums import (
    ConversationStatus,
    ConversationType,
    MessageRole,
)
from conversation.services.conversation_service import ConversationService


User = get_user_model()


class ConversationServiceTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="engineer",
            email="engineer@example.com",
            password="password123",
        )

    def test_create_global_conversation(self):
        conversation = ConversationService.create_global_conversation(
            owner=self.user,
        )

        self.assertEqual(
            conversation.owner,
            self.user,
        )

        self.assertEqual(
            conversation.conversation_type,
            ConversationType.GLOBAL,
        )

        self.assertEqual(
            conversation.status,
            ConversationStatus.ACTIVE,
        )

    def test_create_experiment_conversation(self):
        conversation = ConversationService.create_experiment_conversation(
            owner=self.user,
        )

        self.assertEqual(
            conversation.conversation_type,
            ConversationType.EXPERIMENT,
        )

    def test_create_research_conversation(self):
        conversation = ConversationService.create_research_conversation(
            owner=self.user,
        )

        self.assertEqual(
            conversation.conversation_type,
            ConversationType.RESEARCH,
        )

    def test_add_engineer_message(self):
        conversation = ConversationService.create_global_conversation(
            owner=self.user,
        )

        message = ConversationService.add_engineer_message(
            conversation=conversation,
            content="Reduce weight by 15%",
        )

        self.assertEqual(
            message.role,
            MessageRole.ENGINEER,
        )

        self.assertEqual(
            conversation.messages.count(),
            1,
        )

    def test_add_ai_message(self):
        conversation = ConversationService.create_global_conversation(
            owner=self.user,
        )

        message = ConversationService.add_ai_message(
            conversation=conversation,
            content="Analysis completed.",
        )

        self.assertEqual(
            message.role,
            MessageRole.AI,
        )

    def test_automatic_title_generation(self):
        conversation = ConversationService.create_global_conversation(
            owner=self.user,
        )

        ConversationService.add_engineer_message(
            conversation=conversation,
            content="I want to optimize the production cost of the gearbox housing.",
        )

        conversation.refresh_from_db()

        self.assertNotEqual(
            conversation.title,
            ConversationService.DEFAULT_TITLE,
        )

    def test_close_conversation(self):
        conversation = ConversationService.create_global_conversation(
            owner=self.user,
        )

        ConversationService.close(
            conversation=conversation,
        )

        conversation.refresh_from_db()

        self.assertEqual(
            conversation.status,
            ConversationStatus.CLOSED,
        )

    def test_archive_conversation(self):
        conversation = ConversationService.create_global_conversation(
            owner=self.user,
        )

        ConversationService.archive(
            conversation=conversation,
        )

        conversation.refresh_from_db()

        self.assertEqual(
            conversation.status,
            ConversationStatus.ARCHIVED,
        )

    def test_reopen_conversation(self):
        conversation = ConversationService.create_global_conversation(
            owner=self.user,
        )

        ConversationService.close(
            conversation=conversation,
        )

        ConversationService.reopen(
            conversation=conversation,
        )

        conversation.refresh_from_db()

        self.assertEqual(
            conversation.status,
            ConversationStatus.ACTIVE,
        )

    def test_cannot_add_message_to_closed_conversation(self):
        conversation = ConversationService.create_global_conversation(
            owner=self.user,
        )

        ConversationService.close(
            conversation=conversation,
        )

        with self.assertRaises(Exception):
            ConversationService.add_engineer_message(
                conversation=conversation,
                content="Hello",
            )
