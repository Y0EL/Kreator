from __future__ import annotations

import abc
from collections.abc import AsyncIterator

from app.crawler.request_manager import RequestManager
from app.crawler.types import RawItemData
from app.db.models import Source


class SourceAdapter(abc.ABC):
    type_name: str = "base"

    def __init__(self, source: Source, rm: RequestManager) -> None:
        self.source = source
        self.rm = rm
        self.config: dict = source.parser_config or {}

    @abc.abstractmethod
    def crawl(self) -> AsyncIterator[RawItemData]:
        raise NotImplementedError
