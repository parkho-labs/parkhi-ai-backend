from typing import Dict, Any
from .base_parser import BaseContentParser, ContentParseResult
from ..services.rag_integration_service import RAGIntegrationService


class CollectionParser(BaseContentParser):

    def __init__(self):
        self.rag_service = RAGIntegrationService()

    async def parse(self, source: str, **kwargs) -> ContentParseResult:
        try:
            user_id = kwargs.get('user_id', 'default_user')
            embeddings = await self.rag_service.get_embeddings(source, user_id, 100)

            if not embeddings:
                return ContentParseResult("", error="No files exist in the knowledge base")

            chunks = [f"{e.get('source', 'Unknown')}: {e.get('text', '')}" for e in embeddings if e.get('text')]
            content = "\n\n".join(chunks)

            return ContentParseResult(
                content=content,
                title=f"Collection: {source}",
                metadata={"collection_name": source, "chunk_count": len(chunks), "source_type": "collection"}
            )
        except Exception as e:
            return ContentParseResult("", error=f"Failed to parse collection: {str(e)}")

    def supports_source(self, source: str) -> bool:
        return isinstance(source, str) and source.strip() != ""

    @property
    def supported_types(self) -> list[str]:
        return ["collection"]