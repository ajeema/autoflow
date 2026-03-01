#!/usr/bin/env python3
"""
AutoFlow Context Source: AWS S3 Integration

This example demonstrates how to pull context from AWS S3 for AutoFlow.

Use cases:
- Storing and retrieving historical event logs
- Loading training/validation datasets for evaluation
- Retrieving configuration files from S3
- Archiving workflow execution snapshots
- Cross-region context sharing

Setup:
    pip install boto3
    export AWS_ACCESS_KEY_ID=your_key
    export AWS_SECRET_ACCESS_KEY=your_secret
    export AWS_REGION=us-east-1

For local development:
    docker run -d -p 4566:4566 localstack/localstack
    export AWS_ENDPOINT_URL=http://localhost:4566
"""

import os
import sys
import json
import gzip
import asyncio
from pathlib import Path
from typing import Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))


# =============================================================================
# S3 Context Source
# =============================================================================

@dataclass
class S3Context:
    """Context retrieved from S3."""
    bucket: str
    key: str
    content: Any
    metadata: dict[str, Any]
    last_modified: datetime
    size_bytes: int
    etag: Optional[str] = None


class S3ContextSource:
    """
    Context source that pulls data from AWS S3 or S3-compatible storage.

    Supports:
    - JSON files (automatically parsed)
    - Gzipped files (automatically decompressed)
    - Plain text files
    - Binary files (as bytes)
    """

    def __init__(
        self,
        bucket: str,
        prefix: str = "autoflow/context/",
        region: str = "us-east-1",
        endpoint_url: Optional[str] = None,
    ):
        """
        Initialize S3 context source.

        Args:
            bucket: S3 bucket name
            prefix: Key prefix for AutoFlow context
            region: AWS region
            endpoint_url: Custom endpoint (for LocalStack, MinIO, etc.)
        """
        self.bucket = bucket
        self.prefix = prefix.rstrip("/") + "/"
        self.region = region
        self.endpoint_url = endpoint_url or os.getenv("AWS_ENDPOINT_URL")

        try:
            import boto3
            from botocore.config import Config

            # Configure boto3
            config = Config(
                region_name=region,
                retries={"max_attempts": 3, "mode": "adaptive"},
            )

            session_kwargs = {"region_name": region}
            if self.endpoint_url:
                session_kwargs["endpoint_url"] = self.endpoint_url

            self.s3_client = boto3.client("s3", **session_kwargs, config=config)
            self.s3_resource = boto3.resource("s3", **session_kwargs)

        except ImportError:
            raise ImportError("boto3 required: pip install boto3")

    async def get_context(
        self,
        key: str,
        parse_json: bool = True,
    ) -> Optional[S3Context]:
        """Get context from S3 by key."""

        full_key = f"{self.prefix}{key}"

        try:
            response = self.s3_client.get_object(
                Bucket=self.bucket,
                Key=full_key,
            )

            content_bytes = response["Body"].read()
            content = content_bytes

            # Auto-decompress if gzipped
            if full_key.endswith(".gz"):
                content = gzip.decompress(content_bytes)

            # Parse JSON if requested
            if parse_json and (full_key.endswith(".json") or
                              full_key.endswith(".json.gz")):
                content = json.loads(content.decode("utf-8"))

            return S3Context(
                bucket=self.bucket,
                key=key,
                content=content,
                metadata=response.get("Metadata", {}),
                last_modified=response["LastModified"],
                size_bytes=response["ContentLength"],
                etag=response.get("ETag", "").strip('"'),
            )

        except self.s3_client.exceptions.NoSuchKey:
            print(f"Key not found: {full_key}")
            return None
        except Exception as e:
            print(f"Error getting context from S3: {e}")
            return None

    async def list_contexts(
        self,
        prefix: str = "",
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """List available contexts in S3."""

        full_prefix = f"{self.prefix}{prefix}"

        try:
            paginator = self.s3_client.get_paginator("list_objects_v2")
            pages = paginator.paginate(
                Bucket=self.bucket,
                Prefix=full_prefix,
                MaxKeys=limit,
            )

            contexts = []
            for page in pages:
                for obj in page.get("Contents", []):
                    contexts.append({
                        "key": obj["Key"][len(self.prefix):],
                        "last_modified": obj["LastModified"],
                        "size_bytes": obj["Size"],
                        "etag": obj["ETag"].strip('"'),
                    })

            return contexts[:limit]

        except Exception as e:
            print(f"Error listing contexts from S3: {e}")
            return []

    async def put_context(
        self,
        key: str,
        content: Any,
        metadata: Optional[dict[str, Any]] = None,
        compress: bool = False,
    ) -> bool:
        """Store context to S3."""

        full_key = f"{self.prefix}{key}"

        try:
            # Convert content to bytes
            if isinstance(content, (dict, list)):
                body = json.dumps(content).encode("utf-8")
                if compress:
                    full_key += ".gz"
            elif isinstance(content, str):
                body = content.encode("utf-8")
                if compress:
                    full_key += ".gz"
            elif isinstance(content, bytes):
                body = content
                if compress:
                    full_key += ".gz"
            else:
                raise ValueError(f"Unsupported content type: {type(content)}")

            # Compress if requested
            if compress:
                body = gzip.compress(body)

            # Upload to S3
            kwargs = {"Bucket": self.bucket, "Key": full_key, "Body": body}
            if metadata:
                kwargs["Metadata"] = {k: str(v) for k, v in metadata.items()}

            self.s3_client.put_object(**kwargs)

            return True

        except Exception as e:
            print(f"Error putting context to S3: {e}")
            return False

    async def get_recent_contexts(
        self,
        hours: int = 24,
        prefix: str = "",
    ) -> list[S3Context]:
        """Get contexts modified in the last N hours."""

        contexts = await self.list_contexts(prefix=prefix)
        cutoff = datetime.utcnow() - timedelta(hours=hours)

        recent = []
        for ctx in contexts:
            if ctx["last_modified"] >= cutoff:
                context = await self.get_context(ctx["key"])
                if context:
                    recent.append(context)

        return recent


# =============================================================================
# S3-Backed Replay Dataset
# =============================================================================

class S3ReplayDataset:
    """
    Replay dataset backed by S3 storage.

    This allows you to:
    1. Store historical run data in S3
    2. Load it for evaluation and replay
    3. Share datasets across regions/teams
    """

    def __init__(
        self,
        s3_source: S3ContextSource,
        dataset_prefix: str = "datasets/replay/",
    ):
        self.s3_source = s3_source
        self.dataset_prefix = dataset_prefix

    async def load_dataset(
        self,
        dataset_name: str,
    ) -> Optional[list[dict]]:
        """Load a replay dataset from S3."""

        key = f"{self.dataset_prefix}{dataset_name}.json"
        context = await self.s3_source.get_context(key, parse_json=True)

        if context:
            return context.content
        return None

    async def save_dataset(
        self,
        dataset_name: str,
        runs: list[dict],
        compress: bool = True,
    ) -> bool:
        """Save a replay dataset to S3."""

        key = f"{self.dataset_prefix}{dataset_name}.json"
        return await self.s3_source.put_context(
            key=key,
            content=runs,
            metadata={
                "dataset_name": dataset_name,
                "run_count": str(len(runs)),
                "created_at": datetime.utcnow().isoformat(),
            },
            compress=compress,
        )

    async def list_datasets(self) -> list[str]:
        """List available replay datasets."""

        contexts = await self.s3_source.list_contexts(
            prefix=self.dataset_prefix,
        )

        return [
            ctx["key"].replace(self.dataset_prefix, "").replace(".json", "")
            for ctx in contexts
            if ctx["key"].startswith(self.dataset_prefix) and
               ctx["key"].endswith(".json")
        ]


# =============================================================================
# S3 Configuration Store
# =============================================================================

class S3ConfigurationStore:
    """
    Store and retrieve configuration files from S3.

    Use cases:
    - Centralized configuration management
    - Version-controlled configs
    - Environment-specific settings
    - Shared configurations across instances
    """

    def __init__(
        self,
        s3_source: S3ContextSource,
        config_prefix: str = "config/",
    ):
        self.s3_source = s3_source
        self.config_prefix = config_prefix

    async def get_config(
        self,
        config_name: str,
        environment: str = "production",
    ) -> Optional[dict]:
        """Get configuration from S3."""

        key = f"{self.config_prefix}{environment}/{config_name}.json"
        context = await self.s3_source.get_context(key, parse_json=True)

        return context.content if context else None

    async def put_config(
        self,
        config_name: str,
        config: dict,
        environment: str = "production",
    ) -> bool:
        """Store configuration to S3."""

        key = f"{self.config_prefix}{environment}/{config_name}.json"
        return await self.s3_source.put_context(
            key=key,
            content=config,
            metadata={
                "environment": environment,
                "config_name": config_name,
            },
        )

    async def list_configs(
        self,
        environment: Optional[str] = None,
    ) -> list[str]:
        """List available configurations."""

        prefix = f"{self.config_prefix}{environment}/" if environment else ""
        contexts = await self.s3_source.list_contexts(prefix=prefix)

        return [
            ctx["key"]
            .replace(self.config_prefix, "")
            .replace(".json", "")
            for ctx in contexts
        ]


# =============================================================================
# S3 Event Log Archiver
# =============================================================================

class S3EventArchiver:
    """
    Archive AutoFlow events to S3 for long-term storage and analysis.

    Benefits:
    - Durable, scalable event storage
    - Cost-effective with S3 lifecycle policies
    - Easy analytics with Athena/Redshift Spectrum
    - Cross-region replication for disaster recovery
    """

    def __init__(
        self,
        s3_source: S3ContextSource,
        archive_prefix: str = "archive/events/",
        batch_size: int = 1000,
    ):
        self.s3_source = s3_source
        self.archive_prefix = archive_prefix
        self.batch_size = batch_size
        self._buffer: list[dict] = []

    async def archive_event(self, event: dict) -> bool:
        """Archive a single event to S3."""

        # Add to buffer
        self._buffer.append({
            "timestamp": datetime.utcnow().isoformat(),
            "event": event,
        })

        # Flush if buffer is full
        if len(self._buffer) >= self.batch_size:
            return await self._flush_buffer()

        return True

    async def _flush_buffer(self) -> bool:
        """Flush buffered events to S3."""

        if not self._buffer:
            return True

        # Create filename with timestamp
        timestamp = datetime.utcnow().strftime("%Y/%m/%d/%H%M%S")
        key = f"{self.archive_prefix}{timestamp}.json"

        success = await self.s3_source.put_context(
            key=key,
            content=self._buffer,
            compress=True,
        )

        if success:
            self._buffer.clear()

        return success

    async def archive_events(self, events: list[dict]) -> bool:
        """Archive multiple events to S3."""

        for event in events:
            await self.archive_event(event)

        # Flush any remaining events
        return await self._flush_buffer()

    async def query_archived_events(
        self,
        start_date: datetime,
        end_date: datetime,
        filters: Optional[dict[str, Any]] = None,
    ) -> list[dict]:
        """Query archived events by date range."""

        # Build prefix for date range
        prefix = f"{self.archive_prefix}{start_date.strftime('%Y/%m/%d')}/"

        # List all event files in range
        contexts = await self.s3_source.list_contexts(prefix=prefix)

        # Load and filter events
        all_events = []
        for ctx in contexts:
            context = await self.s3_source.get_context(ctx["key"], parse_json=True)
            if context and context.content:
                for entry in context.content:
                    # Apply filters
                    if filters:
                        event_data = entry.get("event", {})
                        match = all(
                            str(event_data.get(k)) == str(v)
                            for k, v in filters.items()
                        )
                        if not match:
                            continue
                    all_events.append(entry)

        return all_events


# =============================================================================
# Example Usage
# =============================================================================

async def example_s3_context_source():
    """Example of using S3 as a context source."""

    print("=" * 70)
    print("AutoFlow S3 Context Source Example")
    print("=" * 70)
    print()

    # Initialize S3 context source
    # For local development with LocalStack
    endpoint_url = os.getenv("AWS_ENDPOINT_URL", "http://localhost:4566")
    bucket = os.getenv("S3_BUCKET", "autoflow-context")

    print(f"1. Initializing S3 context source...")
    print(f"   Bucket: {bucket}")
    print(f"   Endpoint: {endpoint_url}")

    s3_source = S3ContextSource(
        bucket=bucket,
        prefix="autoflow/context/",
        endpoint_url=endpoint_url,
    )
    print("   ✓ S3 context source initialized")

    # Store some context
    print("\n2. Storing context to S3...")
    await s3_source.put_context(
        key="example_config",
        content={
            "workflow_name": "example_workflow",
            "threshold": 5,
            "rules": ["HighErrorRateRetryRule", "SlowStepRule"],
        },
        metadata={"version": "1.0"},
    )
    print("   ✓ Context stored")

    # Retrieve context
    print("\n3. Retrieving context from S3...")
    context = await s3_source.get_context("example_config")
    if context:
        print(f"   ✓ Context retrieved")
        print(f"   Content: {json.dumps(context.content, indent=2)}")

    # List all contexts
    print("\n4. Listing all contexts...")
    contexts = await s3_source.list_contexts()
    print(f"   Found {len(contexts)} context(s):")
    for ctx in contexts:
        print(f"   - {ctx['key']} ({ctx['size_bytes']} bytes)")


async def example_s3_replay_dataset():
    """Example of using S3-backed replay dataset."""

    print("\n" + "=" * 70)
    print("S3-Backed Replay Dataset Example")
    print("=" * 70)
    print()

    bucket = os.getenv("S3_BUCKET", "autoflow-context")
    endpoint_url = os.getenv("AWS_ENDPOINT_URL", "http://localhost:4566")

    s3_source = S3ContextSource(
        bucket=bucket,
        endpoint_url=endpoint_url,
    )

    replay_dataset = S3ReplayDataset(s3_source)

    # Create a sample dataset
    print("1. Creating replay dataset...")
    sample_runs = [
        {
            "run_id": "run_001",
            "workflow_id": "test_workflow",
            "success": True,
            "latency_ms": 100,
            "error": None,
        },
        {
            "run_id": "run_002",
            "workflow_id": "test_workflow",
            "success": False,
            "latency_ms": 5000,
            "error": "timeout",
        },
        {
            "run_id": "run_003",
            "workflow_id": "test_workflow",
            "success": True,
            "latency_ms": 120,
            "error": None,
        },
    ]

    await replay_dataset.save_dataset(
        dataset_name="sample_workflow_runs",
        runs=sample_runs,
        compress=True,
    )
    print("   ✓ Dataset saved to S3")

    # List datasets
    print("\n2. Listing available datasets...")
    datasets = await replay_dataset.list_datasets()
    print(f"   Found {len(datasets)} dataset(s):")
    for ds in datasets:
        print(f"   - {ds}")

    # Load dataset
    print("\n3. Loading dataset...")
    loaded_runs = await replay_dataset.load_dataset("sample_workflow_runs")
    if loaded_runs:
        print(f"   ✓ Loaded {len(loaded_runs)} runs")
        print(f"   Success rate: {sum(1 for r in loaded_runs if r['success']) / len(loaded_runs):.1%}")


async def example_s3_config_store():
    """Example of using S3 configuration store."""

    print("\n" + "=" * 70)
    print("S3 Configuration Store Example")
    print("=" * 70)
    print()

    bucket = os.getenv("S3_BUCKET", "autoflow-context")
    endpoint_url = os.getenv("AWS_ENDPOINT_URL", "http://localhost:4566")

    s3_source = S3ContextSource(
        bucket=bucket,
        endpoint_url=endpoint_url,
    )

    config_store = S3ConfigurationStore(s3_source)

    # Store configurations for different environments
    print("1. Storing configurations...")
    for env in ["development", "staging", "production"]:
        config = {
            "environment": env,
            "threshold": 5 if env == "production" else 10,
            "log_level": "INFO" if env == "production" else "DEBUG",
            "enable_metrics": env == "production",
        }

        await config_store.put_config(
            config_name="workflow_config",
            config=config,
            environment=env,
        )
        print(f"   ✓ {env} configuration stored")

    # List configs
    print("\n2. Listing configurations...")
    configs = await config_store.list_configs()
    print(f"   Found {len(configs)} configuration(s):")
    for cfg in configs:
        print(f"   - {cfg}")

    # Get production config
    print("\n3. Loading production configuration...")
    prod_config = await config_store.get_config(
        config_name="workflow_config",
        environment="production",
    )
    if prod_config:
        print(f"   ✓ Production config loaded")
        print(f"   Threshold: {prod_config['threshold']}")
        print(f"   Log level: {prod_config['log_level']}")


async def example_s3_event_archiver():
    """Example of archiving events to S3."""

    print("\n" + "=" * 70)
    print("S3 Event Archiver Example")
    print("=" * 70)
    print()

    bucket = os.getenv("S3_BUCKET", "autoflow-context")
    endpoint_url = os.getenv("AWS_ENDPOINT_URL", "http://localhost:4566")

    s3_source = S3ContextSource(
        bucket=bucket,
        endpoint_url=endpoint_url,
    )

    archiver = S3EventArchiver(s3_source)

    # Archive some events
    print("1. Archiving events...")
    sample_events = [
        {
            "source": "workflow",
            "name": "step_completed",
            "attributes": {"step": "data_processing"},
        },
        {
            "source": "workflow",
            "name": "step_failed",
            "attributes": {"step": "model_inference", "error": "timeout"},
        },
        {
            "source": "workflow",
            "name": "step_completed",
            "attributes": {"step": "result_storage"},
        },
    ]

    for event in sample_events:
        await archiver.archive_event(event)

    # Flush remaining events
    await archiver._flush_buffer()
    print("   ✓ Events archived")

    # Query archived events
    print("\n2. Querying archived events...")
    archived = await archiver.query_archived_events(
        start_date=datetime.utcnow() - timedelta(hours=1),
        end_date=datetime.utcnow(),
    )
    print(f"   Found {len(archived)} archived event(s)")


# =============================================================================
# Terraform/CloudFormation for Infrastructure
# =============================================================================

def generate_terraform_config():
    """
    Generate Terraform configuration for setting up S3 infrastructure.
    """

    terraform = """
# Terraform configuration for AutoFlow S3 context storage

terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# S3 bucket for AutoFlow context
resource "aws_s3_bucket" "autoflow_context" {
  bucket = var.bucket_name

  tags = {
    Name        = "AutoFlow Context Bucket"
    Environment = var.environment
    Application = "autoflow"
  }
}

# Enable versioning for configuration history
resource "aws_s3_bucket_versioning" "autoflow_context" {
  bucket = aws_s3_bucket.autoflow_context.id

  versioning_configuration {
    status = "Enabled"
  }
}

# Enable server-side encryption
resource "aws_s3_bucket_server_side_encryption" "autoflow_context" {
  bucket = aws_s3_bucket.autoflow_context.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Lifecycle policy for cost optimization
resource "aws_s3_bucket_lifecycle_configuration" "autoflow_context" {
  bucket = aws_s3_bucket.autoflow_context.id

  rule {
    id     = "archive_old_data"
    status = "Enabled"

    # Transition old data to Glacier
    transition {
      days          = 90
      storage_class = "GLACIER"
    }

    # Delete very old data
    expiration {
      days = 365
    }
  }
}

# IAM policy for AutoFlow service
resource "aws_iam_policy" "autoflow_s3_access" {
  name        = "AutoFlowS3Access"
  description = "Policy for AutoFlow to access S3 context bucket"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:ListBucket",
        ]
        Resource = [
          aws_s3_bucket.autoflow_context.arn,
          "${aws_s3_bucket.autoflow_context.arn}/*",
        ]
      }
    ]
  })
}

# Variables
variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "bucket_name" {
  description = "S3 bucket name for AutoFlow context"
  type        = string
  default     = "autoflow-context-prod"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "production"
}

# Outputs
output "bucket_name" {
  value = aws_s3_bucket.autoflow_context.id
}

output "bucket_arn" {
  value = aws_s3_bucket.autoflow_context.arn
}

output "iam_policy_arn" {
  value = aws_iam_policy.autoflow_s3_access.arn
}
"""

    print(terraform)


# =============================================================================
# Main Entry Point
# =============================================================================

async def main():
    """Run the S3 context source examples."""

    await example_s3_context_source()
    await example_s3_replay_dataset()
    await example_s3_config_store()
    await example_s3_event_archiver()

    print("\n" + "=" * 70)
    print("Infrastructure as Code")
    print("=" * 70)
    print("\nTerraform configuration for S3 infrastructure:")
    print("(Save to main.tf and run: terraform apply)")
    print()
    generate_terraform_config()

    print("\n" + "=" * 70)
    print("Examples completed!")
    print("=" * 70)
    print("\nTo use S3 context in production:")
    print("  1. Create S3 bucket using Terraform (or CloudFormation)")
    print("  2. Configure IAM credentials for AutoFlow")
    print("  3. Set environment variables:")
    print("     export AWS_ACCESS_KEY_ID=your_key")
    print("     export AWS_SECRET_ACCESS_KEY=your_secret")
    print("     export S3_BUCKET=your-bucket-name")
    print("  4. Use S3ContextSource in your AutoFlow engine")


if __name__ == "__main__":
    asyncio.run(main())
