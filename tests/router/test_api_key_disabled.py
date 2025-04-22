import unittest
from unittest.mock import MagicMock, patch

from mcpm.router.transport import RouterSseTransport


class TestApiKeyDisabled(unittest.TestCase):
    """Test that API key validation is disabled when api_key is set to None."""

    def test_api_key_disabled(self):
        """Test that API key validation is disabled when api_key is set to None."""
        # Create a transport with api_key=None
        transport = RouterSseTransport("/messages/", api_key=None)
        
        # Mock the scope
        scope = MagicMock()
        
        # Test that _validate_api_key returns True regardless of the api_key parameter
        self.assertTrue(transport._validate_api_key(scope, api_key=None))
        self.assertTrue(transport._validate_api_key(scope, api_key="some-key"))
        self.assertTrue(transport._validate_api_key(scope, api_key="invalid-key"))

    def test_api_key_enabled(self):
        """Test that API key validation works when api_key is set."""
        # Create a transport with a specific api_key
        transport = RouterSseTransport("/messages/", api_key="test-key")
        
        # Mock the scope
        scope = MagicMock()
        
        # Test that _validate_api_key returns True only for the matching key
        self.assertTrue(transport._validate_api_key(scope, api_key="test-key"))
        self.assertFalse(transport._validate_api_key(scope, api_key="wrong-key"))
        
        # When using the default validation logic, we need to mock the ConfigManager
        with patch("mcpm.router.transport.ConfigManager") as mock_config_manager:
            # Set up the mock to make the default validation logic fail
            mock_instance = mock_config_manager.return_value
            mock_instance.read_share_config.return_value = {"url": "http://example.com", "api_key": "share-key"}
            mock_instance.get_router_config.return_value = {"host": "localhost"}
            
            # Test with a key that doesn't match the transport's key
            self.assertFalse(transport._validate_api_key(scope, api_key="wrong-key"))


if __name__ == "__main__":
    unittest.main()