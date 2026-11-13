"""Store and search vectors using PostgreSQL + pgvector."""
import json
from typing import Any
from urllib.parse import urlsplit

import pg8000.native

from .models import Chunk


class PgVectorStore:
    def __init__(self, database_url: str, dimensions: int) -> None:
        self.database_url = database_url
        self.dimensions = dimensions
        parsed = urlsplit(database_url)
        self.user = parsed.username or "day6"
        self.password = parsed.password or "day6_local_only"
        self.host = parsed.hostname or "127.0.0.1"
        self.port = parsed.port or 55433
        self.database = parsed.path.lstrip("/") or "day6_lab"

    def _get_connection(self) -> pg8000.native.Connection:
        return pg8000.native.Connection(
            user=self.user,
            password=self.password,
            host=self.host,
            port=self.port,
            database=self.database
        )

    def create_schema(self) -> None:
        """Create extension and chunks table with vector column and metadata."""
        conn = self._get_connection()
        try:
            conn.run("CREATE EXTENSION IF NOT EXISTS vector;")
            conn.run(f"""
                CREATE TABLE IF NOT EXISTS chunks (
                    id TEXT PRIMARY KEY,
                    strategy TEXT NOT NULL,
                    chunk_id TEXT NOT NULL,
                    document_id TEXT NOT NULL,
                    source TEXT NOT NULL,
                    page INT NOT NULL,
                    text TEXT NOT NULL,
                    metadata JSONB NOT NULL DEFAULT '{{}}'::jsonb,
                    embedding vector({self.dimensions})
                );
            """)
            conn.run("CREATE INDEX IF NOT EXISTS idx_chunks_strategy ON chunks(strategy);")
        finally:
            conn.close()

    def upsert(self, strategy: str, chunks: list[Chunk], vectors: list[list[float]]) -> None:
        """Validate lengths and write stable IDs without duplicates. Remove obsolete chunks."""
        if len(chunks) != len(vectors):
            raise ValueError(f"Length mismatch: {len(chunks)} chunks vs {len(vectors)} vectors.")

        conn = self._get_connection()
        try:
            current_ids = set()
            for chunk, vec in zip(chunks, vectors):
                stable_id = f"{strategy}_{chunk.chunk_id}"
                current_ids.add(stable_id)
                vec_str = "[" + ",".join(str(x) for x in vec) + "]"
                meta_json = json.dumps(chunk.metadata, ensure_ascii=False)

                sql = """
                    INSERT INTO chunks (id, strategy, chunk_id, document_id, source, page, text, metadata, embedding)
                    VALUES (:id, :strategy, :chunk_id, :document_id, :source, :page, :text, :metadata::jsonb, :embedding::vector)
                    ON CONFLICT (id) DO UPDATE SET
                        text = EXCLUDED.text,
                        metadata = EXCLUDED.metadata,
                        embedding = EXCLUDED.embedding;
                """
                conn.run(
                    sql,
                    id=stable_id,
                    strategy=strategy,
                    chunk_id=chunk.chunk_id,
                    document_id=chunk.document_id,
                    source=chunk.source,
                    page=chunk.page,
                    text=chunk.text.replace("\x00", ""),
                    metadata=meta_json,
                    embedding=vec_str
                )

            # Clean up obsolete chunks for this strategy
            existing_rows = conn.run("SELECT id FROM chunks WHERE strategy = :strategy", strategy=strategy)
            for row in existing_rows:
                cid = row[0]
                if cid not in current_ids:
                    conn.run("DELETE FROM chunks WHERE id = :id", id=cid)

        finally:
            conn.close()

    def search(self, strategy: str, query_vector: list[float], top_k: int = 3,
               filters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """Filter metadata in SQL, rank by cosine distance, and return top-k."""
        conn = self._get_connection()
        try:
            vec_str = "[" + ",".join(str(x) for x in query_vector) + "]"

            if filters:
                filter_json = json.dumps(filters, ensure_ascii=False)
                sql = """
                    SELECT chunk_id, text, 1 - (embedding <=> :qvec::vector) AS score,
                           document_id, source, page, metadata
                    FROM chunks
                    WHERE strategy = :strategy AND metadata @> :filter_json::jsonb
                    ORDER BY embedding <=> :qvec::vector ASC
                    LIMIT :top_k;
                """
                rows = conn.run(sql, strategy=strategy, qvec=vec_str, filter_json=filter_json, top_k=top_k)
            else:
                sql = """
                    SELECT chunk_id, text, 1 - (embedding <=> :qvec::vector) AS score,
                           document_id, source, page, metadata
                    FROM chunks
                    WHERE strategy = :strategy
                    ORDER BY embedding <=> :qvec::vector ASC
                    LIMIT :top_k;
                """
                rows = conn.run(sql, strategy=strategy, qvec=vec_str, top_k=top_k)

            results: list[dict[str, Any]] = []
            for row in rows:
                results.append({
                    "chunk_id": row[0],
                    "text": row[1],
                    "score": float(row[2]),
                    "document_id": row[3],
                    "source": row[4],
                    "page": int(row[5]),
                    "metadata": row[6] if isinstance(row[6], dict) else json.loads(row[6])
                })
            return results
        finally:
            conn.close()
