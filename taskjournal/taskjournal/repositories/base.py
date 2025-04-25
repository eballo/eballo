from abc import ABC, abstractmethod
from typing import List

from taskjournal.models.task import Task


class TaskRepository(ABC):
    @abstractmethod
    def add(self, task: Task) -> None: ...

    @abstractmethod
    def list_all(self) -> List[Task]: ...

    @abstractmethod
    def update(self, task: Task) -> None: ...
