from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class ContentParseResult:
    """Result of content parsing operation."""

    def __init__(
        self,
        content: str,
        title: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None
    ):
        self.content = content
        self.title = title
        self.metadata = metadata or {}
        self.error = error
        self.success = error is None

    def __repr__(self):
        status = "Success" if self.success else f"Error: {self.error}"
        return f"ContentParseResult({status}, content_length={len(self.content)})"


class BaseContentParser(ABC):
    """Abstract base class for content parsers."""

    @abstractmethod
    async def parse(self, source: str, **kwargs) -> ContentParseResult:
        """
        Parse content from the given source.

        Args:
            source: The source to parse (file path, URL, etc.)
            **kwargs: Additional parser-specific parameters

        Returns:
            ContentParseResult with extracted content and metadata
        """
        pass

    @abstractmethod
    def supports_source(self, source: str) -> bool:
        """
        Check if this parser can handle the given source.

        Args:
            source: The source to check

        Returns:
            True if this parser can handle the source
        """
        pass

    @property
    @abstractmethod
    def supported_types(self) -> list[str]:
        """
        Get list of content types this parser supports.

        Returns:
            List of supported content type strings
        """
        pass