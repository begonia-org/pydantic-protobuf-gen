"""
Test configuration for client tests
"""
import pytest
import asyncio

# Configure pytest-asyncio
pytest_plugins = ('pytest_asyncio',)


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# Server connection settings
SERVER_BASE_URL = "http://localhost:8010"
SERVER_TIMEOUT = 30.0
