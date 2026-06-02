"""S3 client configured for SSE-KMS buckets (Signature Version 4 required for presigned URLs)."""

from __future__ import annotations

import boto3
from botocore.client import BaseClient, Config

_S3_CONFIG = Config(signature_version="s3v4")


def s3_client() -> BaseClient:
    return boto3.client("s3", config=_S3_CONFIG)
