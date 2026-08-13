"""
GitHub App Service

Handles GitHub App authentication and installation management.
Uses JWT authentication to get installation tokens.
"""
import os
import time
import jwt
import requests
from typing import Optional, Dict, List, Any
from utils.logger import get_logger

logger = get_logger(__name__)


class GitHubAppService:
    """
    Service for managing GitHub App authentication and installations.
    
    GitHub Apps use a two-step authentication process:
    1. Generate a JWT using the App's private key
    2. Exchange JWT for an installation access token
    """
    
    def __init__(self):
        self.app_id = os.environ.get('GITHUB_APP_ID')
        self.private_key = self._load_private_key()
        self.webhook_secret = os.environ.get('GITHUB_APP_WEBHOOK_SECRET', '')
        self.client_id = os.environ.get('GITHUB_APP_CLIENT_ID')
        self.client_secret = os.environ.get('GITHUB_APP_CLIENT_SECRET')
        
        # Base URLs
        self.api_base = 'https://api.github.com'
    
    def _load_private_key(self) -> str:
        """Load private key from environment variable."""
        key = os.environ.get('GITHUB_APP_PRIVATE_KEY', '')
        if key:
            # Handle escaped newlines from .env file
            key = key.replace('\\n', '\n')
        return key
        
    def is_configured(self) -> bool:
        """Check if GitHub App is properly configured."""
        return bool(self.app_id and self.private_key)
    
    def generate_jwt(self) -> str:
        """
        Generate a JWT for GitHub App authentication.
        JWT is valid for 10 minutes (max allowed by GitHub).
        """
        if not self.app_id or not self.private_key:
            raise ValueError("GitHub App ID and Private Key are required")
        
        now = int(time.time())
        payload = {
            'iat': now - 60,  # Issued 60 seconds ago (clock drift tolerance)
            'exp': now + (10 * 60),  # Expires in 10 minutes
            'iss': self.app_id
        }
        
        token = jwt.encode(payload, self.private_key, algorithm='RS256')
        return token
    
    def get_app_info(self) -> Dict[str, Any]:
        """Get information about the GitHub App."""
        jwt_token = self.generate_jwt()
        
        response = requests.get(
            f'{self.api_base}/app',
            headers={
                'Authorization': f'Bearer {jwt_token}',
                'Accept': 'application/vnd.github+json',
                'X-GitHub-Api-Version': '2022-11-28'
            }
        )
        response.raise_for_status()
        return response.json()
    
    def list_installations(self) -> List[Dict[str, Any]]:
        """List all installations of this GitHub App."""
        jwt_token = self.generate_jwt()
        
        response = requests.get(
            f'{self.api_base}/app/installations',
            headers={
                'Authorization': f'Bearer {jwt_token}',
                'Accept': 'application/vnd.github+json',
                'X-GitHub-Api-Version': '2022-11-28'
            }
        )
        response.raise_for_status()
        return response.json()
    
    def get_installation_for_user(self, username: str) -> Optional[Dict[str, Any]]:
        """Get installation for a specific user/organization."""
        installations = self.list_installations()
        
        for installation in installations:
            account = installation.get('account', {})
            if account.get('login', '').lower() == username.lower():
                return installation
        
        return None
    
    def get_installation_access_token(self, installation_id: int) -> Dict[str, Any]:
        """
        Get an access token for a specific installation.
        This token can be used to make API calls on behalf of the installation.
        """
        jwt_token = self.generate_jwt()
        
        response = requests.post(
            f'{self.api_base}/app/installations/{installation_id}/access_tokens',
            headers={
                'Authorization': f'Bearer {jwt_token}',
                'Accept': 'application/vnd.github+json',
                'X-GitHub-Api-Version': '2022-11-28'
            }
        )
        response.raise_for_status()
        return response.json()
    
    def get_installation_repos(self, installation_id: int) -> List[Dict[str, Any]]:
        """Get all repositories accessible by an installation."""
        token_data = self.get_installation_access_token(installation_id)
        access_token = token_data['token']
        
        repos = []
        page = 1
        per_page = 100
        
        while True:
            response = requests.get(
                f'{self.api_base}/installation/repositories',
                headers={
                    'Authorization': f'token {access_token}',
                    'Accept': 'application/vnd.github+json',
                    'X-GitHub-Api-Version': '2022-11-28'
                },
                params={'page': page, 'per_page': per_page}
            )
            response.raise_for_status()
            data = response.json()
            
            repos.extend(data.get('repositories', []))
            
            if len(data.get('repositories', [])) < per_page:
                break
            page += 1
        
        return repos
    
    def get_installation_url(self) -> str:
        """Get the URL where users can install the GitHub App."""
        if not self.app_id:
            raise ValueError("GitHub App ID is required")
        
        # Get the app slug from app info
        try:
            app_info = self.get_app_info()
            slug = app_info.get('slug', '')
            return f'https://github.com/apps/{slug}/installations/new'
        except Exception:
            # Fallback - user needs to find the app manually
            return 'https://github.com/settings/apps'
    
    def verify_webhook_signature(self, payload: bytes, signature: str) -> bool:
        """Verify the webhook payload signature."""
        if not self.webhook_secret or not signature:
            return False
        
        import hmac
        import hashlib
        
        if signature.startswith('sha256='):
            signature = signature[7:]
        
        expected = hmac.new(
            self.webhook_secret.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(expected, signature)


# Singleton instance
_github_app_service: Optional[GitHubAppService] = None


def get_github_app_service() -> GitHubAppService:
    """Get or create the GitHub App service singleton."""
    global _github_app_service
    if _github_app_service is None:
        _github_app_service = GitHubAppService()
    return _github_app_service
