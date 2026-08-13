import pytest
from unittest.mock import patch, MagicMock
import jwt
import time
import os
from services.github_app import GitHubAppService, get_github_app_service

@pytest.fixture
def mock_env():
    with patch.dict(os.environ, {
        'GITHUB_APP_ID': '12345',
        'GITHUB_APP_PRIVATE_KEY': '-----BEGIN RSA PRIVATE KEY-----\nMIIEpAIBAAKCAQEA7V...\n-----END RSA PRIVATE KEY-----',
        'GITHUB_APP_WEBHOOK_SECRET': 'test_secret',
        'GITHUB_APP_CLIENT_ID': 'client_id',
        'GITHUB_APP_CLIENT_SECRET': 'client_secret'
    }):
        yield

def test_github_app_init(mock_env):
    service = GitHubAppService()
    assert service.app_id == '12345'
    assert service.webhook_secret == 'test_secret'
    assert service.is_configured() is True

def test_generate_jwt(mock_env):
    service = GitHubAppService()
    with patch('jwt.encode', return_value='mocked_jwt') as mock_jwt_encode:
        token = service.generate_jwt()
        assert token == 'mocked_jwt'
        mock_jwt_encode.assert_called_once()
        args, kwargs = mock_jwt_encode.call_args
        assert args[0]['iss'] == '12345'
        assert kwargs['algorithm'] == 'RS256'

def test_verify_webhook_signature(mock_env):
    service = GitHubAppService()
    payload = b'{"action": "opened"}'
    
    # Correct signature for 'test_secret' and payload
    import hmac
    import hashlib
    expected = hmac.new(b'test_secret', payload, hashlib.sha256).hexdigest()
    signature = f'sha256={expected}'
    
    assert service.verify_webhook_signature(payload, signature) is True
    assert service.verify_webhook_signature(payload, 'sha256=invalid') is False

@patch('requests.get')
def test_get_app_info(mock_get, mock_env):
    service = GitHubAppService()
    mock_response = MagicMock()
    mock_response.json.return_value = {'slug': 'test-app'}
    mock_response.raise_for_status.return_value = None
    mock_get.return_value = mock_response
    
    with patch.object(GitHubAppService, 'generate_jwt', return_value='mock_jwt'):
        info = service.get_app_info()
        assert info['slug'] == 'test-app'
        mock_get.assert_called_once_with(
            'https://api.github.com/app',
            headers={
                'Authorization': 'Bearer mock_jwt',
                'Accept': 'application/vnd.github+json',
                'X-GitHub-Api-Version': '2022-11-28'
            }
        )

@patch('requests.post')
def test_get_installation_access_token(mock_post, mock_env):
    service = GitHubAppService()
    mock_response = MagicMock()
    mock_response.json.return_value = {'token': 'access_token_123', 'expires_at': '2024-01-01T00:00:00Z'}
    mock_response.raise_for_status.return_value = None
    mock_post.return_value = mock_response
    
    with patch.object(GitHubAppService, 'generate_jwt', return_value='mock_jwt'):
        token_data = service.get_installation_access_token(123456)
        assert token_data['token'] == 'access_token_123'
        mock_post.assert_called_once_with(
            'https://api.github.com/app/installations/123456/access_tokens',
            headers={
                'Authorization': 'Bearer mock_jwt',
                'Accept': 'application/vnd.github+json',
                'X-GitHub-Api-Version': '2022-11-28'
            }
        )
