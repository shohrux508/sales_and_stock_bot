from collections.abc import Callable
from typing import Any

from fastapi import Request


class Container:
    def __init__(self):
        self._services: dict[str, Any] = {}

    def register(self, name: str, instance: Any) -> None:
        if name in self._services:
            raise ValueError(f"Service '{name}' already registered")
        self._services[name] = instance

    def get(self, name: str) -> Any:
        if name not in self._services:
            raise ValueError(f"Service '{name}' not found")
        return self._services[name]

    def resolve(self, name: str) -> Callable:
        """FastAPI Depends() da foydalanish uchun metod"""
        def _resolve(request: Request) -> Any:
            return request.app.state.container.get(name)
        return _resolve
