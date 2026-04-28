"""Hello unit test module."""

from shared_python.hello import hello


def test_hello():
    """Test the hello function."""
    assert hello() == "Hello shared-python"
