from abc import ABC, abstractmethod
from typing import List, Dict


class BaseCollector(ABC):

    @abstractmethod
    async def fetch(self) -> List[Dict]:
        pass