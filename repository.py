from abc import ABC, abstractmethod
from typing import Optional


class TaskRepository(ABC):
    """Interface every storage backend must implement.
    Routes and services only ever talk to this contract."""

    @abstractmethod
    def get_all(self, done: Optional[bool] = None, search: Optional[str] = None) -> list[dict]:
        ...

    @abstractmethod
    def get(self, task_id: int) -> Optional[dict]:
        ...

    @abstractmethod
    def create(self, title: str) -> dict:
        ...

    @abstractmethod
    def update(self, task_id: int, title: Optional[str], done: Optional[bool]) -> Optional[dict]:
        ...

    @abstractmethod
    def delete(self, task_id: int) -> bool:
        ...

    @abstractmethod
    def stats(self) -> dict:
        ...