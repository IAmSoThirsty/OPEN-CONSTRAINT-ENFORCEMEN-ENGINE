"""
Tests for microservice features: metrics, health checks, configuration.
"""
import unittest
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Set test environment variables before importing app
os.environ['METRICS_ENABLED'] = 'true'
os.environ['RATE_LIMIT_ENABLED'] = 'false'  # Disable for tests
os.environ['LOG_FORMAT'] = 'text'

from config import Config
import app_production


class TestConfiguration(unittest.TestCase):
    """Test configuration management."""

    def test_config_validation(self):
        """Test configuration validation."""
        Config.validate()
        self.assertGreater(Config.WORKERS, 0)
        self.assertIn(Config.LOG_FORMAT, ['json', 'text'])

    def test_environment_override(self):
        """Test environment variable override."""
        self.assertEqual(os.getenv('METRICS_ENABLED'), 'true')


class TestHealthEndpoints(unittest.TestCase):
    """Test health check endpoints."""

    @classmethod
    def setUpClass(cls):
        """Set up test client."""
        app_production.app.config['TESTING'] = True
        cls.client = app_production.app.test_client()

    def test_liveness_probe(self):
        """Test liveness probe endpoint."""
        response = self.client.get('/health')
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.data)
        self.assertEqual(data['status'], 'healthy')

    def test_readiness_probe(self):
        """Test readiness probe endpoint."""
        response = self.client.get('/ready')
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.data)
        self.assertEqual(data['status'], 'ready')
        self.assertIn('policies_loaded', data)
        self.assertGreater(data['policies_loaded'], 0)


class TestMetrics(unittest.TestCase):
    """Test Prometheus metrics endpoint."""

    @classmethod
    def setUpClass(cls):
        """Set up test client."""
        app_production.app.config['TESTING'] = True
        cls.client = app_production.app.test_client()

    def test_metrics_endpoint(self):
        """Test metrics endpoint returns data."""
        response = self.client.get('/metrics')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'policy_evaluations_total', response.data)
        self.assertIn(b'policy_evaluation_latency_seconds', response.data)


class TestEvaluationWithMetrics(unittest.TestCase):
    """Test evaluation with metrics collection."""

    @classmethod
    def setUpClass(cls):
        """Set up test client."""
        app_production.app.config['TESTING'] = True
        cls.client = app_production.app.test_client()

    def test_successful_evaluation_with_metrics(self):
        """Test that successful evaluation increments metrics."""
        request_data = {
            "actor_id": "user123",
            "action_type": "mutation",
            "payload": {
                "actor": {"max_role": 10},
                "request": {"role": 5, "value": 500}
            },
            "policy_id": "mutation_policy_v1"
        }

        # Get initial metrics
        metrics_before = self.client.get('/metrics').data

        # Make evaluation request
        response = self.client.post(
            '/evaluate',
            data=json.dumps(request_data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.data)
        self.assertTrue(data['allowed'])

        # Get updated metrics
        metrics_after = self.client.get('/metrics').data

        # Verify metrics were updated
        self.assertNotEqual(metrics_before, metrics_after)


class TestRequestLimits(unittest.TestCase):
    """Test request size limits."""

    @classmethod
    def setUpClass(cls):
        """Set up test client."""
        app_production.app.config['TESTING'] = True
        cls.client = app_production.app.test_client()

    def test_oversized_request(self):
        """Test that oversized requests are rejected."""
        # Create a payload larger than MAX_CONTENT_LENGTH
        large_payload = {
            "actor_id": "user123",
            "action_type": "mutation",
            "payload": {
                "data": "x" * (Config.MAX_CONTENT_LENGTH + 1000)
            },
            "policy_id": "mutation_policy_v1"
        }

        response = self.client.post(
            '/evaluate',
            data=json.dumps(large_payload),
            content_type='application/json'
        )

        # Flask returns 413 or 500 for oversized requests depending on when it's caught
        self.assertIn(response.status_code, [413, 500])


class TestThreadSafety(unittest.TestCase):
    """Test thread safety of components."""

    def test_initialization_thread_safety(self):
        """Test that component initialization is thread-safe."""
        import threading

        results = []

        def init_component():
            try:
                app_production.initialize_components()
                results.append('success')
            except Exception as e:
                results.append(f'error: {e}')

        threads = [threading.Thread(target=init_component) for _ in range(10)]

        for t in threads:
            t.start()

        for t in threads:
            t.join()

        # All threads should succeed
        self.assertEqual(len(results), 10)
        self.assertTrue(all(r == 'success' for r in results))


class TestDeterminism(unittest.TestCase):
    """Test deterministic behavior."""

    @classmethod
    def setUpClass(cls):
        """Set up test client."""
        app_production.app.config['TESTING'] = True
        cls.client = app_production.app.test_client()

    def test_hash_consistency(self):
        """Test that same inputs produce same hash."""
        request_data = {
            "actor_id": "user123",
            "action_type": "mutation",
            "payload": {
                "actor": {"max_role": 10},
                "request": {"role": 5, "value": 500}
            },
            "policy_id": "mutation_policy_v1"
        }

        # Make same request multiple times
        hashes = []
        for _ in range(5):
            response = self.client.post(
                '/evaluate',
                data=json.dumps(request_data),
                content_type='application/json'
            )
            data = json.loads(response.data)
            hashes.append(data['simulation_hash'])

        # All hashes should be identical
        self.assertEqual(len(set(hashes)), 1)


if __name__ == '__main__':
    unittest.main()
