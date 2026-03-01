import json
import sqlite3
from typing import Sequence, Optional

from autoflow.errors import StorageError
from autoflow.types import ContextGraphDelta, GraphNode, GraphEdge


class SQLiteGraphStore:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        self._init_db()

    def _init_db(self) -> None:
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            cur.execute("""
                CREATE TABLE IF NOT EXISTS nodes (
                    node_id TEXT PRIMARY KEY,
                    node_type TEXT NOT NULL,
                    properties TEXT NOT NULL
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS edges (
                    edge_id TEXT PRIMARY KEY,
                    edge_type TEXT NOT NULL,
                    from_node_id TEXT NOT NULL,
                    to_node_id TEXT NOT NULL,
                    properties TEXT NOT NULL,
                    FOREIGN KEY (from_node_id) REFERENCES nodes(node_id),
                    FOREIGN KEY (to_node_id) REFERENCES nodes(node_id)
                )
            """)
            conn.commit()
            conn.close()
        except sqlite3.Error as e:
            raise StorageError(str(e)) from e

    def upsert(self, delta: ContextGraphDelta) -> None:
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        # Upsert nodes
        for node in delta.nodes:
            cur.execute("""
                INSERT OR REPLACE INTO nodes(node_id, node_type, properties)
                VALUES (?, ?, ?)
            """, (node.node_id, node.node_type, json.dumps(dict(node.properties))))

        # Upsert edges
        for edge in delta.edges:
            from uuid import uuid4
            edge_id = f"{edge.from_node_id}->{edge.to_node_id}"
            cur.execute("""
                INSERT OR REPLACE INTO edges(edge_id, edge_type, from_node_id, to_node_id, properties)
                VALUES (?, ?, ?, ?, ?)
            """, (edge_id, edge.edge_type, edge.from_node_id, edge.to_node_id,
                  json.dumps(dict(edge.properties))))

        conn.commit()
        conn.close()

    def query_nodes(
        self,
        node_type: Optional[str] = None,
        limit: int = 100,
    ) -> Sequence[GraphNode]:
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        if node_type:
            cur.execute("""
                SELECT node_id, node_type, properties FROM nodes
                WHERE node_type=? LIMIT ?
            """, (node_type, limit))
        else:
            cur.execute("""
                SELECT node_id, node_type, properties FROM nodes
                LIMIT ?
            """, (limit,))

        rows = cur.fetchall()
        conn.close()

        return [
            GraphNode(node_id=r[0], node_type=r[1], properties=json.loads(r[2]))
            for r in rows
        ]

    def query_edges(
        self,
        edge_type: Optional[str] = None,
        limit: int = 100,
    ) -> Sequence[GraphEdge]:
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()

        if edge_type:
            cur.execute("""
                SELECT edge_type, from_node_id, to_node_id, properties FROM edges
                WHERE edge_type=? LIMIT ?
            """, (edge_type, limit))
        else:
            cur.execute("""
                SELECT edge_type, from_node_id, to_node_id, properties FROM edges
                LIMIT ?
            """, (limit,))

        rows = cur.fetchall()
        conn.close()

        return [
            GraphEdge(edge_type=r[0], from_node_id=r[1], to_node_id=r[2], properties=json.loads(r[3]))
            for r in rows
        ]