"""RAG retriever using ChromaDB."""
import os
from typing import List, Optional
from dataclasses import dataclass
import chromadb
from chromadb.config import Settings

from .embeddings import EmbeddingModel


@dataclass
class Document:
    id: str
    content: str
    metadata: dict


@dataclass
class SearchResult:
    document: Document
    score: float


class RAGRetriever:
    def __init__(
        self,
        persist_dir: str = "./chroma_db",
        collection_name: str = "documents"
    ):
        self.persist_dir = persist_dir
        self.collection_name = collection_name
        self.embedding_model = EmbeddingModel()

        # Initialize ChromaDB
        os.makedirs(persist_dir, exist_ok=True)
        self.client = chromadb.PersistentClient(path=persist_dir)
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"}
        )

    async def add_documents(self, documents: List[Document]) -> None:
        """Add documents to the collection."""
        if not documents:
            return

        ids = [doc.id for doc in documents]
        contents = [doc.content for doc in documents]
        metadatas = [doc.metadata for doc in documents]

        # Generate embeddings
        embeddings = self.embedding_model.embed(contents)

        self.collection.add(
            ids=ids,
            documents=contents,
            embeddings=embeddings,
            metadatas=metadatas
        )

    async def search(
        self,
        query: str,
        top_k: int = 5
    ) -> List[dict]:
        """Search for relevant documents."""
        query_embedding = self.embedding_model.embed_single(query)

        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=["documents", "metadatas", "distances"]
        )

        search_results = []
        if results["documents"] and results["documents"][0]:
            for i, doc in enumerate(results["documents"][0]):
                search_results.append({
                    "content": doc,
                    "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                    "score": 1 - results["distances"][0][i] if results["distances"] else 0
                })

        return search_results

    async def delete_document(self, doc_id: str) -> None:
        """Delete a document by ID."""
        self.collection.delete(ids=[doc_id])

    async def get_document_count(self) -> int:
        """Get total document count."""
        return self.collection.count()
