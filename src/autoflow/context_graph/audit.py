"""
Audit logging for Context Graph Framework.

Tracks all operations for security, compliance, and debugging.
Supports multiple backends and is designed to be low-overhead.

Enhanced with querying, aggregation, and export capabilities.
"""

from abc import ABC, abstractmethod
from collections import defaultdict
from datetime import datetime
from enum import Enum
import gzip
import inspect
import json
import os
import shutil
import sqlite3
import threading
import time
from queue import Queue
from typing import Any, Optional, Callable, Generator

# Pydantic for validation and serialization
from pydantic import BaseModel, Field, ConfigDict


class AuditEventType(str, Enum):
    """Types of audit events."""

    # Authentication events
    AUTH_SUCCESS = "auth_success"
    AUTH_FAILURE = "auth_failure"
    AUTH_EXPIRED = "auth_expired"

    # Authorization events
    AUTHZ_GRANTED = "authz_granted"
    AUTHZ_DENIED = "authz_denied"

    # Read operations
    ENTITY_READ = "entity_read"
    RELATIONSHIP_READ = "relationship_read"
    GRAPH_TRAVERSE = "graph_traverse"
    GRAPH_QUERY = "graph_query"
    GRAPH_SEARCH = "graph_search"

    # Write operations
    ENTITY_CREATED = "entity_created"
    ENTITY_UPDATED = "entity_updated"
    ENTITY_DELETED = "entity_deleted"
    RELATIONSHIP_CREATED = "relationship_created"
    RELATIONSHIP_UPDATED = "relationship_updated"
    RELATIONSHIP_DELETED = "relationship_deleted"

    # Schema operations
    SCHEMA_MODIFIED = "schema_modified"

    # Admin operations
    USER_ADDED = "user_added"
    USER_REMOVED = "user_removed"
    PERMISSIONS_GRANTED = "permissions_granted"
    PERMISSIONS_REVOKED = "permissions_revoked"

    # Security events
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    INJECTION_ATTEMPT = "injection_attempt"


class AuditEvent(BaseModel):
    """
    An audit event record.

    Created automatically or manually for tracking.
    """

    # Pydantic configuration
    model_config = ConfigDict(
        validate_assignment=True,
        extra="forbid",
        arbitrary_types_allowed=True,
        use_enum_values=True,
    )

    event_type: AuditEventType
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    user_id: Optional[str] = None
    username: Optional[str] = None
    session_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None

    # Operation details
    operation: Optional[str] = None  # e.g., "create_entity", "traverse"
    resource_type: Optional[str] = None  # e.g., "entity", "relationship"
    resource_id: Optional[str] = None  # e.g., entity ID

    # Request details
    success: bool = True
    error_message: Optional[str] = None
    error_code: Optional[str] = None

    # Additional context
    metadata: dict[str, Any] = Field(default_factory=dict)

    # Performance metrics
    duration_ms: Optional[float] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "event_type": self.event_type.value if isinstance(self.event_type, AuditEventType) else self.event_type,
            "timestamp": self.timestamp.isoformat(),
            "user_id": self.user_id,
            "username": self.username,
            "session_id": self.session_id,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "operation": self.operation,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "success": self.success,
            "error_message": self.error_message,
            "error_code": self.error_code,
            "metadata": self.metadata,
            "duration_ms": self.duration_ms,
        }

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict())


class AuditBackend(ABC):
    """Abstract base for audit backends."""

    @abstractmethod
    def write(self, event: AuditEvent) -> None:
        """Write an audit event."""
        pass

    @abstractmethod
    def close(self) -> None:
        """Close the backend."""
        pass


class FileAuditBackend(AuditBackend):
    """
    Write audit logs to a file.

    Simple and reliable. Supports rotation.
    """

    def __init__(
        self,
        filepath: str = "audit.log",
        rotate: bool = True,
        max_size_mb: int = 100,
    ):
        """
        Initialize file audit backend.

        Args:
            filepath: Path to log file
            rotate: Whether to rotate logs when they get too large
            max_size_mb: Max size before rotation
        """
        self.filepath = filepath
        self.rotate = rotate
        self.max_size_bytes = max_size_mb * 1024 * 1024

    def write(self, event: AuditEvent) -> None:
        """Write event to file."""
        try:
            # Check rotation
            if self.rotate:
                try:
                    if os.path.exists(self.filepath):
                        size = os.path.getsize(self.filepath)
                        if size > self.max_size_bytes:
                            self._rotate()
                except OSError:
                    pass

            with open(self.filepath, "a") as f:
                f.write(event.to_json() + "\n")
        except Exception as e:
            # Don't crash the app if logging fails
            print(f"Failed to write audit log: {e}")

    def _rotate(self) -> None:
        """Rotate log file."""

        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        backup_path = f"{self.filepath}.{timestamp}"

        try:
            shutil.move(self.filepath, backup_path)

            # Compress old logs
            try:
                with open(backup_path, "rb") as f_in:
                    with gzip.open(f"{backup_path}.gz", "wb") as f_out:
                        shutil.copyfileobj(f_in, f_out)
                os.remove(backup_path)
            except Exception:
                # Keep uncompressed if gzip fails
                pass
        except Exception:
            pass

    def close(self) -> None:
        """Close the file backend."""
        pass  # Nothing to close for files


class DatabaseAuditBackend(AuditBackend):
    """
    Write audit logs to a database.

    Supports SQL databases and can be extended for NoSQL.
    """

    def __init__(
        self,
        connection_string: str,
        table_name: str = "audit_logs",
        batch_size: int = 100,
    ):
        """
        Initialize database audit backend.

        Args:
            connection_string: Database connection string
            table_name: Table to write logs to
            batch_size: Number of events to batch before writing

        Note:
            Requires appropriate database driver (e.g., psycopg2 for Postgres)
        """
        self.connection_string = connection_string
        self.table_name = table_name
        self.batch_size = batch_size
        self._batch: list[AuditEvent] = []
        self._lock = threading.Lock()

    def write(self, event: AuditEvent) -> None:
        """Add event to batch."""
        with self._lock:
            self._batch.append(event)
            if len(self._batch) >= self.batch_size:
                self._flush()

    def _flush(self) -> None:
        """Write batched events to database."""
        if not self._batch:
            return

        try:
            # Placeholder for actual DB write
            # In production, use connection pool and proper SQL
            conn = sqlite3.connect(":memory:")  # In-memory for demo
            cursor = conn.cursor()

            # Create table if needed
            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS {self.table_name} (
                    event_type TEXT,
                    timestamp TEXT,
                    user_id TEXT,
                    operation TEXT,
                    resource_type TEXT,
                    resource_id TEXT,
                    success BOOLEAN,
                    metadata TEXT
                )
            """)

            # Insert batch
            for event in self._batch:
                cursor.execute(f"""
                    INSERT INTO {self.table_name} VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    event.event_type.value,
                    event.timestamp.isoformat(),
                    event.user_id,
                    event.operation,
                    event.resource_type,
                    event.resource_id,
                    event.success,
                    json.dumps(event.metadata),
                ))

            conn.commit()
            conn.close()

            self._batch.clear()

        except Exception as e:
            print(f"Failed to write audit log to database: {e}")

    def close(self) -> None:
        """Close the database backend."""
        with self._lock:
            self._flush()


class AsyncAuditBackend(AuditBackend):
    """
    Async audit backend that writes in a background thread.

    Prevents logging from blocking operations.
    """

    def __init__(
        self,
        backend: AuditBackend,
        queue_size: int = 10000,
    ):
        """
        Initialize async audit backend.

        Args:
            backend: The underlying backend to write to
            queue_size: Max size of event queue
        """
        self.backend = backend
        self._queue: Queue = Queue(maxsize=queue_size)
        self._running = True
        self._thread = threading.Thread(target=self._worker, daemon=True)
        self._thread.start()

    def _worker(self) -> None:
        """Background worker that writes events."""
        while self._running:
            try:
                event = self._queue.get(timeout=1)
                if event is None:  # Shutdown signal
                    break
                self.backend.write(event)
            except Exception:
                continue  # Keep running despite errors

    def write(self, event: AuditEvent) -> None:
        """Queue event for background writing."""
        try:
            self._queue.put_nowait(event)
        except Exception:
            # Queue full, drop event (or could block)
            pass

    def close(self) -> None:
        """Close the async backend."""
        self._running = False
        self._queue.put(None)  # Signal shutdown
        self._thread.join(timeout=5)
        self.backend.close()


class Auditor:
    """
    Main audit logging interface.

    Provides convenient methods for logging different event types.
    """

    def __init__(
        self,
        backend: Optional[AuditBackend] = None,
        enabled: bool = True,
        include_timestamps: bool = True,
        include_caller_info: bool = True,
    ):
        """
        Initialize auditor.

        Args:
            backend: The backend to write logs to (default: file)
            enabled: Whether logging is enabled
            include_timestamps: Add timestamps to events
            include_caller_info: Add caller info to events
        """
        self.backend = backend or FileAuditBackend()
        self.enabled = enabled
        self.include_timestamps = include_timestamps
        self.include_caller_info = include_caller_info

    def log(
        self,
        event_type: AuditEventType,
        operation: Optional[str] = None,
        user_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        success: bool = True,
        error_message: Optional[str] = None,
        error_code: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
        duration_ms: Optional[float] = None,
    ) -> AuditEvent:
        """
        Log an audit event.

        Args:
            event_type: Type of event
            operation: Operation being performed
            user_id: User performing the operation
            resource_type: Type of resource
            resource_id: ID of resource
            success: Whether operation succeeded
            error_message: Error message if failed
            error_code: Error code if failed
            metadata: Additional context
            duration_ms: Operation duration

        Returns:
            The created AuditEvent
        """
        if not self.enabled:
            return AuditEvent(event_type=event_type)

        event = AuditEvent(
            event_type=event_type,
            operation=operation,
            user_id=user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            success=success,
            error_message=error_message,
            error_code=error_code,
            metadata=metadata or {},
            duration_ms=duration_ms,
        )

        if self.include_caller_info:
            frame = inspect.currentframe()
            if frame and frame.f_back:
                caller = frame.f_back
                event.metadata["caller_file"] = caller.f_code.co_filename
                event.metadata["caller_line"] = caller.f_lineno
                event.metadata["caller_function"] = caller.f_code.co_name

        self.backend.write(event)
        return event

    def log_auth(
        self,
        success: bool,
        user_id: Optional[str] = None,
        error_message: Optional[str] = None,
        **kwargs
    ) -> AuditEvent:
        """Log authentication event."""
        event_type = AuditEventType.AUTH_SUCCESS if success else AuditEventType.AUTH_FAILURE
        return self.log(
            event_type=event_type,
            operation="authenticate",
            user_id=user_id,
            success=success,
            error_message=error_message,
            metadata=kwargs,
        )

    def log_authz(
        self,
        granted: bool,
        user_id: Optional[str] = None,
        permission: Optional[str] = None,
        resource_id: Optional[str] = None,
        **kwargs
    ) -> AuditEvent:
        """Log authorization event."""
        event_type = AuditEventType.AUTHZ_GRANTED if granted else AuditEventType.AUTHZ_DENIED
        return self.log(
            event_type=event_type,
            operation="authorize",
            user_id=user_id,
            resource_id=resource_id,
            success=granted,
            metadata={"permission": permission, **kwargs},
        )

    def log_read(
        self,
        resource_type: str,
        resource_id: Optional[str] = None,
        user_id: Optional[str] = None,
        **kwargs
    ) -> AuditEvent:
        """Log read operation."""
        return self.log(
            event_type=AuditEventType.ENTITY_READ if resource_type == "entity" else AuditEventType.RELATIONSHIP_READ,
            operation="read",
            user_id=user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            metadata=kwargs,
        )

    def log_write(
        self,
        resource_type: str,
        resource_id: Optional[str] = None,
        user_id: Optional[str] = None,
        **kwargs
    ) -> AuditEvent:
        """Log write operation."""
        return self.log(
            event_type=AuditEventType.ENTITY_CREATED if resource_type == "entity" else AuditEventType.RELATIONSHIP_CREATED,
            operation="create",
            user_id=user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            metadata=kwargs,
        )

    def log_security_event(
        self,
        event_type: AuditEventType,
        details: str,
        user_id: Optional[str] = None,
        **kwargs
    ) -> AuditEvent:
        """Log security event."""
        return self.log(
            event_type=event_type,
            operation="security",
            user_id=user_id,
            error_message=details,
            metadata=kwargs,
        )

    def close(self) -> None:
        """Close the auditor."""
        self.backend.close()

    def query_events(
        self,
        event_type: Optional[AuditEventType] = None,
        user_id: Optional[str] = None,
        operation: Optional[str] = None,
        resource_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        success: Optional[bool] = None,
        limit: int = 1000,
    ) -> list[AuditEvent]:
        """
        Query audit events with filters.

        Note: This is a basic implementation. For production use with large audit logs,
        implement database-specific querying.

        Args:
            event_type: Filter by event type
            user_id: Filter by user
            operation: Filter by operation name
            resource_id: Filter by resource ID
            start_time: Start time filter (inclusive)
            end_time: End time filter (inclusive)
            success: Filter by success status
            limit: Maximum number of results

        Returns:
            List of matching audit events
        """
        # For file-based backends, we need to read and parse
        # For database backends, we'd query with SQL
        results = []

        # If using FileAuditBackend, we can read and parse
        if isinstance(self.backend, FileAuditBackend):
            try:
                with open(self.backend.filepath, "r") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue

                        try:
                            data = json.loads(line)
                            event = AuditEvent(**data)

                            # Apply filters
                            if event_type and event.event_type != event_type:
                                continue
                            if user_id and event.user_id != user_id:
                                continue
                            if operation and event.operation != operation:
                                continue
                            if resource_id and event.resource_id != resource_id:
                                continue
                            if start_time and event.timestamp < start_time:
                                continue
                            if end_time and event.timestamp > end_time:
                                continue
                            if success is not None and event.success != success:
                                continue

                            results.append(event)
                            if len(results) >= limit:
                                break

                        except (json.JSONDecodeError, TypeError):
                            continue

            except FileNotFoundError:
                pass

        # Sort by timestamp descending
        results.sort(key=lambda e: e.timestamp, reverse=True)

        return results[:limit]

    def aggregate_by_user(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> dict[str, dict[str, Any]]:
        """
        Aggregate audit events by user.

        Args:
            start_time: Start time for aggregation
            end_time: End time for aggregation

        Returns:
            Dictionary mapping user_id to aggregate stats
        """
        events = self.query_events(start_time=start_time, end_time=end_time, limit=10000)

        user_stats: dict[str, dict[str, Any]] = {}

        for event in events:
            user_id = event.user_id or "anonymous"

            if user_id not in user_stats:
                user_stats[user_id] = {
                    "total_operations": 0,
                    "successful_operations": 0,
                    "failed_operations": 0,
                    "operations": defaultdict(int),
                    "first_seen": event.timestamp,
                    "last_seen": event.timestamp,
                }

            stats = user_stats[user_id]
            stats["total_operations"] += 1

            if event.success:
                stats["successful_operations"] += 1
            else:
                stats["failed_operations"] += 1

            stats["operations"][event.operation or "unknown"] += 1

            if event.timestamp < stats["first_seen"]:
                stats["first_seen"] = event.timestamp
            if event.timestamp > stats["last_seen"]:
                stats["last_seen"] = event.timestamp

        # Convert defaultdicts to regular dicts
        for stats in user_stats.values():
            stats["operations"] = dict(stats["operations"])

        return user_stats

    def aggregate_by_operation(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> dict[str, dict[str, Any]]:
        """
        Aggregate audit events by operation type.

        Args:
            start_time: Start time for aggregation
            end_time: End time for aggregation

        Returns:
            Dictionary mapping operation name to aggregate stats
        """
        events = self.query_events(start_time=start_time, end_time=end_time, limit=10000)

        operation_stats: dict[str, dict[str, Any]] = {}

        for event in events:
            operation = event.operation or "unknown"

            if operation not in operation_stats:
                operation_stats[operation] = {
                    "total_count": 0,
                    "success_count": 0,
                    "failure_count": 0,
                    "users": set(),
                    "avg_duration_ms": [],
                }

            stats = operation_stats[operation]
            stats["total_count"] += 1

            if event.success:
                stats["success_count"] += 1
            else:
                stats["failure_count"] += 1

            if event.user_id:
                stats["users"].add(event.user_id)

            if event.duration_ms:
                stats["avg_duration_ms"].append(event.duration_ms)

        # Calculate averages and convert sets
        for stats in operation_stats.values():
            stats["unique_users"] = len(stats["users"])
            del stats["users"]

            if stats["avg_duration_ms"]:
                stats["avg_duration_ms"] = sum(stats["avg_duration_ms"]) / len(stats["avg_duration_ms"])
            else:
                stats["avg_duration_ms"] = 0.0

        return operation_stats

    def get_security_events(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> dict[str, list[AuditEvent]]:
        """
        Get security-related events for analysis.

        Args:
            start_time: Start time
            end_time: End time

        Returns:
            Dictionary mapping security event type to events
        """
        security_types = {
            AuditEventType.AUTH_FAILURE,
            AuditEventType.AUTH_EXPIRED,
            AuditEventType.AUTHZ_DENIED,
            AuditEventType.SUSPICIOUS_ACTIVITY,
            AuditEventType.RATE_LIMIT_EXCEEDED,
            AuditEventType.INJECTION_ATTEMPT,
        }

        security_events = defaultdict(list)

        for event_type in security_types:
            events = self.query_events(
                event_type=event_type,
                start_time=start_time,
                end_time=end_time,
                limit=1000,
            )
            security_events[event_type.value] = events

        return dict(security_events)

    def export_to_json(
        self,
        filepath: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> int:
        """
        Export audit events to a JSON file.

        Args:
            filepath: Output file path
            start_time: Optional start time filter
            end_time: Optional end time filter

        Returns:
            Number of events exported
        """
        events = self.query_events(
            start_time=start_time,
            end_time=end_time,
            limit=100000,
        )

        with open(filepath, "w") as f:
            json.dump([e.to_dict() for e in events], f, indent=2)

        return len(events)

    def export_to_prometheus(
        self,
        filepath: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> None:
        """
        Export audit metrics in Prometheus format.

        Creates Prometheus-style metrics from audit events.

        Args:
            filepath: Output file path
            start_time: Optional start time filter
            end_time: Optional end_time filter
        """
        events = self.query_events(
            start_time=start_time,
            end_time=end_time,
            limit=100000,
        )

        # Aggregate metrics
        operations = defaultdict(int)
        users = defaultdict(int)
        errors = defaultdict(int)

        for event in events:
            operations[event.operation or "unknown"] += 1
            if event.user_id:
                users[event.user_id] += 1
            if not event.success:
                errors[event.operation or "unknown"] += 1

        lines = []
        timestamp = int(time.time())

        # Operation counters
        for op, count in operations.items():
            lines.append(
                f'audit_operations_total{{operation="{op}"}} {count} {timestamp}'
            )

        # Error counters
        for op, count in errors.items():
            lines.append(
                f'audit_operations_errors_total{{operation="{op}"}} {count} {timestamp}'
            )

        # User activity
        for user_id, count in users.items():
            lines.append(
                f'audit_user_operations_total{{user_id="{user_id}"}} {count} {timestamp}'
            )

        with open(filepath, "w") as f:
            f.write("\n".join(lines))


class AuditContextManager:
    """
    Context manager for automatic audit logging.

    Usage:
        ```python
        auditor = Auditor()
        with AuditContextManager(auditor, "entity_read", user_id="user123") as ctx:
            # Do work
            ctx.set_result(success=True, duration_ms=42)
        ```
    """

    def __init__(
        self,
        auditor: Auditor,
        event_type: AuditEventType,
        operation: Optional[str] = None,
        user_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
    ):
        self.auditor = auditor
        self.event_type = event_type
        self.operation = operation
        self.user_id = user_id
        self.resource_type = resource_type
        self.resource_id = resource_id
        self._start_time = None
        self._result = None

    def __enter__(self) -> "AuditContextManager":
        self._start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        duration_ms = (time.time() - self._start_time) * 1000 if self._start_time else None

        success = exc_type is None
        error_message = str(exc_val) if exc_val else None

        self.auditor.log(
            event_type=self.event_type,
            operation=self.operation,
            user_id=self.user_id,
            resource_type=self.resource_type,
            resource_id=self.resource_id,
            success=success,
            error_message=error_message,
            duration_ms=duration_ms,
        )

    def set_result(
        self,
        success: bool,
        error_message: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> None:
        """Set the result (for use within context manager)."""
        self._result = {"success": success, "error_message": error_message, "metadata": metadata}


# Global default auditor
default_auditor = Auditor(enabled=False)  # Disabled by default
