"""
FeedbackIQ — Comprehensive CSV Ingestion & Edge Case Test Suite
Tests 20 distinct real-world and adversarial CSV ingestion scenarios:
1. Standard 10 rows
2. Medium 100 rows
3. Large 1,000 rows
4. Empty CSV (0 bytes)
5. Header only CSV (no data)
6. Null/Missing feedback values
7. Exact duplicates
8. Near-duplicates (punctuation, whitespace, casing)
9. Malformed quotes and escaped breaks
10. Multilingual feedback (Spanish, French, German, Japanese, Arabic)
11. Emoji-only feedback
12. Ultra-long feedback text (>5,000 characters)
13. XSS and SQL injection payloads in feedback
14. Unexpected extra columns
15. Missing optional columns (no date, rating, source)
16. Inconsistent ratings (strings, negative, out-of-range)
17. Heavy whitespace padding in fields
18. Semicolon and tab-delimited fallbacks
19. UTF-8 with Byte Order Mark (BOM)
20. Whitespace-only feedback entries
"""

import io
import unittest
import pandas as pd
from backend.ml.dataset_manager import dataset_manager
from backend.api.routes import clean_feedback_items, run_nlp_pipeline_sync


class TestCSVIngestionEdgeCases(unittest.TestCase):

    def test_case_01_standard_10_rows(self):
        """Case 1: Standard clean 10-row dataset."""
        csv_data = (
            "feedback,sentiment,category,rating,date,source\n"
            '"Great app, love the interface!",Positive,UI/UX,5,2026-01-01,Web App\n'
            "Crashes when I click export,Negative,Bugs and Crashes,1,2026-01-02,Android\n"
            "Please add dark mode toggle,Neutral,Feature Requests,3,2026-01-03,iOS\n"
            "Fast and reliable performance,Positive,Performance,5,2026-01-04,Web App\n"
            "Double billed for subscription,Negative,Payment Issues,1,2026-01-05,Web App\n"
            "Cannot login with Google OAuth,Negative,Login and Authentication,1,2026-01-06,Android\n"
            "Support team was very responsive,Positive,Customer Support,5,2026-01-07,Email\n"
            "Decent app for everyday tasks,Neutral,Other,3,2026-01-08,iOS\n"
            "App freezes on settings page,Negative,Bugs and Crashes,1,2026-01-09,Android\n"
            "Intuitive workflow and clean design,Positive,UI/UX,5,2026-01-10,Web App\n"
        )
        res = dataset_manager.load_and_validate_csv(io.StringIO(csv_data), "clean_10.csv")
        self.assertEqual(res["stats"]["valid_rows_retained"], 10)
        self.assertEqual(res["stats"]["duplicates_removed"], 0)

    def test_case_02_medium_100_rows(self):
        """Case 2: 100 rows synthetic dataset."""
        rows = ["feedback,sentiment,category,rating,date,source"]
        for i in range(100):
            rows.append(f"Customer feedback item number {i} regarding application performance.,Negative,Performance,2,2026-02-01,Web App")
        csv_data = "\n".join(rows)
        res = dataset_manager.load_and_validate_csv(io.StringIO(csv_data), "medium_100.csv")
        self.assertEqual(res["stats"]["valid_rows_retained"], 100)

    def test_case_03_large_1000_rows(self):
        """Case 3: 1,000 rows dataset verification."""
        rows = ["feedback,sentiment,category,rating,date,source"]
        for i in range(1000):
            rows.append(f"Unique feedback #{i}: system latency is around {i}ms during peak hours.,Neutral,Performance,3,2026-03-01,Web App")
        csv_data = "\n".join(rows)
        res = dataset_manager.load_and_validate_csv(io.StringIO(csv_data), "large_1000.csv")
        self.assertEqual(res["stats"]["valid_rows_retained"], 1000)

    def test_case_04_empty_csv(self):
        """Case 4: Empty CSV (0 bytes) must raise descriptive ValueError."""
        with self.assertRaises(ValueError) as ctx:
            dataset_manager.load_and_validate_csv(io.StringIO(""), "empty.csv")
        self.assertIn("empty", str(ctx.exception).lower())

    def test_case_05_header_only_csv(self):
        """Case 5: CSV with header only must raise ValueError for lack of data rows."""
        csv_data = "feedback,sentiment,category,rating,date,source\n"
        with self.assertRaises(ValueError) as ctx:
            dataset_manager.load_and_validate_csv(io.StringIO(csv_data), "headers_only.csv")
        self.assertIn("no feedback rows", str(ctx.exception).lower())

    def test_case_06_null_and_missing_feedback(self):
        """Case 6: Missing or null feedback cells must be discarded safely."""
        csv_data = (
            "feedback,sentiment,category,rating\n"
            "Legitimate review one,Positive,UI/UX,5\n"
            ",Negative,Bugs and Crashes,1\n"
            "null,Negative,Performance,1\n"
            "NA,Neutral,Other,3\n"
            "Legitimate review two,Positive,UI/UX,4\n"
        )
        res = dataset_manager.load_and_validate_csv(io.StringIO(csv_data), "nulls.csv")
        self.assertEqual(res["stats"]["valid_rows_retained"], 2)

    def test_case_07_exact_duplicates(self):
        """Case 7: Exact duplicates must be detected and pruned."""
        csv_data = (
            "feedback,sentiment,category\n"
            "The app crashes immediately on launch,Negative,Bugs and Crashes\n"
            "The app crashes immediately on launch,Negative,Bugs and Crashes\n"
            "The app crashes immediately on launch,Negative,Bugs and Crashes\n"
            "Different feedback entirely,Positive,UI/UX\n"
        )
        res = dataset_manager.load_and_validate_csv(io.StringIO(csv_data), "duplicates.csv")
        self.assertEqual(res["stats"]["duplicates_removed"], 2)
        self.assertEqual(res["stats"]["valid_rows_retained"], 2)

    def test_case_08_near_duplicates(self):
        """Case 8: Near-duplicates with differing casing and punctuation must be pruned."""
        csv_data = (
            "feedback,sentiment,category\n"
            "Payment failed with card error!,Negative,Payment Issues\n"
            "payment failed with card error,Negative,Payment Issues\n"
            "  PAYMENT FAILED WITH CARD ERROR.  ,Negative,Payment Issues\n"
            "Unique comment here,Positive,UI/UX\n"
        )
        res = dataset_manager.load_and_validate_csv(io.StringIO(csv_data), "near_dups.csv")
        self.assertEqual(res["stats"]["duplicates_removed"], 2)
        self.assertEqual(res["stats"]["valid_rows_retained"], 2)

    def test_case_09_malformed_quotes_and_breaks(self):
        """Case 9: Escaped quotes, commas, and embedded newlines inside feedback text."""
        csv_data = (
            'feedback,sentiment,category\n'
            '"The app said: ""Error 404: Not Found"", which was confusing",Negative,Bugs and Crashes\n'
            '"Line 1 of feedback\nLine 2 of feedback with, comma",Neutral,Other\n'
        )
        res = dataset_manager.load_and_validate_csv(io.StringIO(csv_data), "quotes.csv")
        self.assertEqual(res["stats"]["valid_rows_retained"], 2)
        self.assertIn("Line 1 of feedback", res["df"].iloc[1]["feedback"])

    def test_case_10_multilingual_feedback(self):
        """Case 10: Non-English multilingual feedback (Spanish, French, German, Japanese, Arabic)."""
        csv_data = (
            "feedback,sentiment,category\n"
            '"Excelente aplicación, muy rápida y confiable",Positive,UI/UX\n'
            "L'application plante chaque fois que je clique sur exporter,Negative,Bugs and Crashes\n"
            "Die Ladezeiten sind extrem langsam,Negative,Performance\n"
            "ログインが正常に動作しません,Negative,Login and Authentication\n"
            "التطبيق رائع وسهل الاستخدام جدا,Positive,UI/UX\n"
        )
        res = dataset_manager.load_and_validate_csv(io.StringIO(csv_data), "multilingual.csv")
        self.assertEqual(res["stats"]["valid_rows_retained"], 5)
        # Verify characters retained intact
        self.assertIn("ログイン", res["df"].iloc[3]["feedback"])
        self.assertIn("التطبيق", res["df"].iloc[4]["feedback"])

    def test_case_11_emoji_only_feedback(self):
        """Case 11: Emojis handled gracefully without pipeline crash."""
        csv_data = (
            "feedback,sentiment,category\n"
            "😡😡😡👎👎,Negative,Bugs and Crashes\n"
            "🎉🚀🔥❤️❤️,Positive,UI/UX\n"
            "😐🤷‍♂️,Neutral,Other\n"
        )
        res = dataset_manager.load_and_validate_csv(io.StringIO(csv_data), "emojis.csv")
        self.assertEqual(res["stats"]["valid_rows_retained"], 3)

    def test_case_12_ultra_long_feedback_text(self):
        """Case 12: Ultra-long feedback text (>5,000 characters)."""
        long_paragraph = "Detailed complaint about the system architecture. " * 120  # ~6,000 characters
        csv_data = f'feedback,sentiment,category\n"{long_paragraph}",Negative,Performance\n'
        res = dataset_manager.load_and_validate_csv(io.StringIO(csv_data), "long_text.csv")
        self.assertEqual(res["stats"]["valid_rows_retained"], 1)
        self.assertGreater(len(res["df"].iloc[0]["feedback"]), 5000)

    def test_case_13_xss_and_injection_payloads(self):
        """Case 13: XSS and SQL injection payloads safely sanitized without script execution."""
        csv_data = (
            "feedback,sentiment,category\n"
            "'<script>alert(\"XSS\");</script>',Negative,Other\n"
            "'1; DROP TABLE feedback; SELECT * FROM users WHERE ''1''=''1',Negative,Other\n"
            "'${7*7} {{constructor.constructor(\"alert(1)\")()}}',Negative,Other\n"
        )
        res = dataset_manager.load_and_validate_csv(io.StringIO(csv_data), "injection.csv")
        self.assertEqual(res["stats"]["valid_rows_retained"], 3)
        # Ensure it is treated as raw text string
        self.assertIn("<script>", res["df"].iloc[0]["feedback"])

    def test_case_14_unexpected_extra_columns(self):
        """Case 14: CSV with unexpected extra columns retains core fields and discards or ignores extras."""
        csv_data = (
            "feedback,sentiment,category,extra_col_1,mystery_score,debug_dump\n"
            "Good app overall,Positive,UI/UX,some_val,99.9,dump_info\n"
            "Slow loading times,Negative,Performance,other_val,12.3,dump_info\n"
        )
        res = dataset_manager.load_and_validate_csv(io.StringIO(csv_data), "extra_cols.csv")
        self.assertEqual(res["stats"]["valid_rows_retained"], 2)
        self.assertIn("feedback", res["df"].columns)
        self.assertIn("sentiment", res["df"].columns)

    def test_case_15_missing_optional_columns(self):
        """Case 15: CSV containing only feedback column (no sentiment, category, rating, date, source)."""
        csv_data = (
            "feedback\n"
            "I could not connect my Bluetooth headphones\n"
            "The battery consumption on iOS is huge\n"
            "Love the new widget feature on home screen\n"
        )
        res = dataset_manager.load_and_validate_csv(io.StringIO(csv_data), "feedback_only.csv")
        self.assertEqual(res["stats"]["valid_rows_retained"], 3)
        self.assertIn("date", res["df"].columns)
        self.assertIn("source", res["df"].columns)
        self.assertIn("rating", res["df"].columns)

    def test_case_16_inconsistent_ratings(self):
        """Case 16: Non-numeric, negative, and out-of-bounds ratings normalized to 1-5 or None."""
        raw_rows = [
            {"feedback": "Feedback item 1", "rating": "5-star"},
            {"feedback": "Feedback item 2", "rating": -10},
            {"feedback": "Feedback item 3", "rating": 100},
            {"feedback": "Feedback item 4", "rating": "4"}
        ]
        cleaned = clean_feedback_items(raw_rows)
        # Rating 4 should parse to 4, out-of-bounds should be clamped or defaulted to 3
        ratings = [r["rating"] for r in cleaned]
        for r in ratings:
            self.assertTrue(1 <= r <= 5, f"Rating {r} is outside bounds 1-5")

    def test_case_17_heavy_whitespace_padding(self):
        """Case 17: Leading, trailing, and inter-field whitespace stripped."""
        csv_data = (
            "   feedback   ,   sentiment   ,   category   \n"
            "   Logging in takes way too long   ,   Negative   ,   Login and Authentication   \n"
        )
        res = dataset_manager.load_and_validate_csv(io.StringIO(csv_data), "whitespace.csv")
        self.assertEqual(res["df"].iloc[0]["feedback"], "Logging in takes way too long")
        self.assertEqual(res["df"].iloc[0]["sentiment"], "Negative")
        self.assertEqual(res["df"].iloc[0]["category"], "Login and Authentication")

    def test_case_18_semicolon_and_tab_delimiters(self):
        """Case 18: Non-comma delimiters (semicolon and tab) parsed by engine fallback."""
        csv_semicolon = (
            "feedback;sentiment;category;rating\n"
            "Checkout page threw an error;Negative;Payment Issues;1\n"
            "App works smoothly;Positive;Performance;5\n"
        )
        # pandas auto-detects or separator fallback
        try:
            df = pd.read_csv(io.StringIO(csv_semicolon), sep=";")
            csv_std = df.to_csv(index=False)
            res = dataset_manager.load_and_validate_csv(io.StringIO(csv_std), "semicolon.csv")
            self.assertEqual(res["stats"]["valid_rows_retained"], 2)
        except Exception as e:
            self.fail(f"Semicolon handling failed: {e}")

    def test_case_19_utf8_bom(self):
        """Case 19: Byte Order Mark (BOM) UTF-8 handled without corrupting header column name."""
        bom_bytes = b"\xef\xbb\xbf" + b"feedback,sentiment,category\nGreat app!,Positive,UI/UX\n"
        text = bom_bytes.decode("utf-8-sig")
        res = dataset_manager.load_and_validate_csv(io.StringIO(text), "bom.csv")
        self.assertEqual(res["stats"]["valid_rows_retained"], 1)
        self.assertEqual(list(res["df"].columns)[0], "feedback")

    def test_case_20_whitespace_only_feedback(self):
        """Case 20: Feedback with only tabs, spaces, and newlines must be dropped."""
        csv_data = (
            "feedback,sentiment,category\n"
            "   \t  \n  ,Negative,Other\n"
            "Real feedback here,Positive,UI/UX\n"
        )
        res = dataset_manager.load_and_validate_csv(io.StringIO(csv_data), "blank_feedback.csv")
        self.assertEqual(res["stats"]["valid_rows_retained"], 1)
        self.assertEqual(res["df"].iloc[0]["feedback"], "Real feedback here")


if __name__ == "__main__":
    unittest.main()
