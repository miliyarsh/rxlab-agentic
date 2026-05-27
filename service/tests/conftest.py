"""Pytest configuration shared by every test suite.

Currently empty by design — pytest picks up ``pythonpath = ["."]`` from
``pyproject.toml`` and that's enough for the unit tests in C1. Fixtures
for ``moto`` (integration tests) will be added in C6.
"""
