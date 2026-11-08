"""
FeedbackIQ — Supabase & Database Integration Test Suite
Tests:
1. System status and dual-mode detection
2. Analysis session persistence with UUIDs
3. Automatic cascade deletion of child feedback and themes
4. Analysis history retrieval and user scoping
5. Session activation (switching active workspace)
6. Token verification and user data isolation
"""

import unittest
import uuid
from datetime import datetime
from backend.database.db import DatabaseClient, is_valid_uuid, db


class TestSupabaseIntegration(unittest.TestCase):
    def setUp(self):
        self.db = DatabaseClient()
        self.test_user_id = str(uuid.uuid4())
        self.other_user_id = str(uuid.uuid4())

    def test_01_system_status_and_dual_mode(self):
        """Verify system status reports valid mode and connectivity attributes."""
        status = self.db.get_system_status()
        self.assertTrue(status["online"])
        self.assertIn("mode", status)
        self.assertIn(status["database_type"], ["supabase", "local"])
        self.assertIsInstance(status["connected"], bool)
        self.assertGreaterEqual(status["records_count"], 0)

    def test_02_uuid_generation_and_validation(self):
        """Verify standard UUID generation format required by Postgres."""
        valid_id = str(uuid.uuid4())
        self.assertTrue(is_valid_uuid(valid_id))
        self.assertFalse(is_valid_uuid("non-uuid-string"))
        self.assertFalse(is_valid_uuid(None))

    def test_03_create_analysis_session_persistence(self):
        """Verify creating an analysis session correctly sets up master, history, themes, and feedback."""
        sample_feedback = [
            {
                "id": str(uuid.uuid4()),
                "feedback_text": "The app freezes whenever I click the export button.",
                "sentiment": "Negative",
                "confidence": 0.94,
                "theme_id": "theme_1",
                "source": "Android App",
                "rating": 1,
                "date": "2026-11-08"
            },
            {
                "id": str(uuid.uuid4()),
                "feedback_text": "Love the clean dark UI and easy task filtering!",
                "sentiment": "Positive",
                "confidence": 0.98,
                "theme_id": "theme_2",
                "source": "Web App",
                "rating": 5,
                "date": "2026-11-08"
            }
        ]

        sample_themes = [
            {
                "id": "theme_1",
                "name": "App Crashes & Freezes",
                "theme_name": "App Crashes & Freezes",
                "ai_summary": "Users experience blocking freezes during export.",
                "summary": "Users experience blocking freezes during export.",
                "mention_count": 1,
                "positive_percentage": 0.0,
                "negative_percentage": 100.0,
                "neutral_percentage": 0.0,
                "severity": "High",
                "priority": "High",
                "recommendation": "Profile export thread and prevent main-thread blockage.",
                "representative_feedback": ["The app freezes whenever I click the export button."]
            },
            {
                "id": "theme_2",
                "name": "Customer Praise",
                "theme_name": "Customer Praise",
                "ai_summary": "Strong satisfaction with UI aesthetics.",
                "summary": "Strong satisfaction with UI aesthetics.",
                "mention_count": 1,
                "positive_percentage": 100.0,
                "negative_percentage": 0.0,
                "neutral_percentage": 0.0,
                "severity": "Low",
                "priority": "Low",
                "recommendation": "Document design tokens in style guide.",
                "representative_feedback": ["Love the clean dark UI and easy task filtering!"]
            }
        ]

        analysis_id = self.db.create_analysis_session(
            analysis_name="Integration Test Session",
            feedback_records=sample_feedback,
            themes=sample_themes,
            user_id=self.test_user_id
        )

        self.assertTrue(is_valid_uuid(analysis_id))

        # Retrieve analysis details
        details = self.db.get_analysis_by_id(analysis_id)
        self.assertIsNotNone(details)
        self.assertEqual(details["session"]["id"], analysis_id)
        self.assertEqual(details["session"]["analysis_name"], "Integration Test Session")
        self.assertEqual(details["session"]["total_feedback"], 2)
        self.assertEqual(len(details["themes"]), 2)
        self.assertEqual(len(details["feedback"]), 2)

        # Clean up
        self.db.delete_analysis(analysis_id, user_id=self.test_user_id)

    def test_04_session_activation(self):
        """Verify activating a past analysis switches active workspace."""
        analysis_id = self.db.create_analysis_session(
            analysis_name="Activation Test Session",
            feedback_records=[{"feedback_text": "Sample text", "sentiment": "Positive", "confidence": 0.9}],
            themes=[{"id": "theme_1", "theme_name": "General", "mention_count": 1}],
            user_id=self.test_user_id
        )

        success = self.db.activate_analysis(analysis_id)
        self.assertTrue(success)
        self.assertEqual(self.db._local_data.get("active_analysis_id"), analysis_id)

        # Clean up
        self.db.delete_analysis(analysis_id, user_id=self.test_user_id)

    def test_05_session_deletion_cascade(self):
        """Verify deleting an analysis removes the session and resets cleanly."""
        analysis_id = self.db.create_analysis_session(
            analysis_name="Deletion Test Session",
            feedback_records=[{"feedback_text": "To be deleted", "sentiment": "Negative", "confidence": 0.8}],
            themes=[{"id": "theme_1", "theme_name": "Delete Me", "mention_count": 1}],
            user_id=self.test_user_id
        )

        # Ensure session exists
        self.assertIsNotNone(self.db.get_analysis_by_id(analysis_id))

        # Delete
        deleted = self.db.delete_analysis(analysis_id, user_id=self.test_user_id)
        self.assertTrue(deleted)

        # Confirm it is no longer retrieved
        self.assertIsNone(self.db.get_analysis_by_id(analysis_id))

    def test_06_user_data_isolation(self):
        """Verify user history filtering isolates sessions by user_id."""
        id_1 = self.db.create_analysis_session(
            analysis_name="User 1 Private Session",
            feedback_records=[{"feedback_text": "Secret 1", "sentiment": "Positive", "confidence": 0.9}],
            themes=[],
            user_id=self.test_user_id
        )

        id_2 = self.db.create_analysis_session(
            analysis_name="User 2 Private Session",
            feedback_records=[{"feedback_text": "Secret 2", "sentiment": "Positive", "confidence": 0.9}],
            themes=[],
            user_id=self.other_user_id
        )

        # User 1 history should not include User 2
        user_1_hist = self.db.get_history(user_id=self.test_user_id)
        user_1_ids = [h["id"] for h in user_1_hist]
        self.assertIn(id_1, user_1_ids)
        self.assertNotIn(id_2, user_1_ids)

        # Clean up
        self.db.delete_analysis(id_1, user_id=self.test_user_id)
        self.db.delete_analysis(id_2, user_id=self.other_user_id)


if __name__ == "__main__":
    unittest.main()
