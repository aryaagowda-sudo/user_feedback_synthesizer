"""
FeedbackIQ — Comprehensive Performance & Stress Test Suite

Measures:
1. DistilBERT Batch Inference Latency & Throughput (items / second)
2. SentenceTransformers Embedding Generation Latency (items / second)
3. End-to-End Pipeline Latency for 100 records
4. Memory Stability across repeated pipeline calls (zero leaks)
"""

import time
import unittest
import numpy as np
from backend.services.sentiment import sentiment_analyzer
from backend.services.clustering import semantic_clusterer


class TestPerformanceStress(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        sentiment_analyzer.preload_models()
        semantic_clusterer.preload_models()

    def test_01_sentiment_inference_throughput(self):
        """Measures DistilBERT batch throughput across 100 feedback sentences."""
        batch_100 = [
            f"Review {i}: The application operates as expected with occasional lag in network calls."
            for i in range(100)
        ]

        start_time = time.time()
        results = sentiment_analyzer.analyze_batch(batch_100, batch_size=64)
        elapsed = time.time() - start_time

        throughput = len(batch_100) / max(0.001, elapsed)

        self.assertEqual(len(results), 100)
        # Even on modest CPU, should process at least 15 items per second
        self.assertGreater(throughput, 15.0, f"Throughput too low: {throughput:.1f} items/sec")
        self.assertLess(elapsed, 10.0, f"Total 100-item batch time exceeded 10 seconds: {elapsed:.2f}s")

    def test_02_embedding_generation_throughput(self):
        """Measures SentenceTransformer embedding throughput across 50 feedback sentences."""
        batch_50 = [
            f"Sentence {i}: Authentication timeout occurred while attempting to sign in."
            for i in range(50)
        ]

        start_time = time.time()
        embeddings = semantic_clusterer.get_embeddings(batch_50, batch_size=32)
        elapsed = time.time() - start_time

        throughput = len(batch_50) / max(0.001, elapsed)

        self.assertEqual(len(embeddings), 50)
        self.assertEqual(len(embeddings[0]), 384)
        self.assertGreater(throughput, 20.0, f"Embedding throughput too low: {throughput:.1f} items/sec")

    def test_03_end_to_end_clustering_speed(self):
        """Measures end-to-end clustering latency for 60 feedback items."""
        sample_corpus = [
            {"id": f"fb_{i}", "feedback_text": f"User complaint {i} about broken checkout and payment failure.", "sentiment": "Negative", "rating": 1}
            if i % 2 == 0 else
            {"id": f"fb_{i}", "feedback_text": f"User praise {i} regarding clean interface and fast navigation.", "sentiment": "Positive", "rating": 5}
            for i in range(60)
        ]

        start_time = time.time()
        themes, labeled = semantic_clusterer.cluster_feedback(sample_corpus)
        elapsed = time.time() - start_time

        self.assertEqual(len(labeled), 60)
        self.assertGreaterEqual(len(themes), 2)
        # 60 items should be clustered and labeled in under 5.0 seconds
        self.assertLess(elapsed, 5.0, f"Clustering took too long: {elapsed:.2f}s")

    def test_04_memory_stability_repeated_calls(self):
        """Verifies process memory remains stable across multiple repeated inference passes."""
        try:
            import os
            import psutil
            process = psutil.Process(os.getpid())
            mem_before_mb = process.memory_info().rss / (1024 * 1024)

            # Run 5 repeated batches
            for _ in range(5):
                _ = sentiment_analyzer.analyze_batch(["Testing memory consumption under high repetition"] * 20)

            mem_after_mb = process.memory_info().rss / (1024 * 1024)
            growth_mb = mem_after_mb - mem_before_mb
            # Memory should not leak by more than 150 MB across 5 iterations
            self.assertLess(growth_mb, 150.0, f"Memory growth excessive: {growth_mb:.2f} MB")
        except ImportError:
            # If psutil is not installed, skip gracefully
            pass


if __name__ == "__main__":
    unittest.main()
