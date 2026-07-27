"""Authentication placeholder - NoopAuthProvider for MVP"""

from abc import ABC, abstractmethod


class AuthProvider(ABC):
    """Authentication provider interface"""

    @abstractmethod
    async def authenticate(self, token: str) -> dict:
        """Authenticate and return user info dict"""
        ...


class NoopAuthProvider(AuthProvider):
    """No-op auth for MVP - always returns system user"""

    async def authenticate(self, token: str) -> dict:
        return {
            "user_id": "system",
            "username": "system",
            "is_admin": True,
        }
