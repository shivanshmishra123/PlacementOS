"""Private S3-Compatible Object Storage Service.

Enforces tenant isolation, quarantine upload isolation, immutable accepted keys,
content hashing, and short-lived presigned access URLs.
"""

from __future__ import annotations

import hashlib
import re
import uuid
from typing import Any

import boto3  # type: ignore[import-untyped]
from botocore.client import Config  # type: ignore[import-untyped]
from botocore.exceptions import ClientError  # type: ignore[import-untyped]

from placementos.core.config import settings


class StorageSecurityError(Exception):
    """Raised when an object storage request violates tenant or key isolation boundaries."""

    pass


class StorageService:
    """Manages object storage operations with strict multi-tenant boundaries."""

    def __init__(
        self,
        endpoint_url: str | None = None,
        access_key_id: str | None = None,
        secret_access_key: str | None = None,
        bucket_name: str | None = None,
        region: str | None = None,
    ) -> None:
        self.endpoint_url = endpoint_url or settings.S3_ENDPOINT_URL
        self.access_key_id = access_key_id or settings.S3_ACCESS_KEY_ID
        self.secret_access_key = secret_access_key or settings.S3_SECRET_ACCESS_KEY
        self.bucket_name = bucket_name or settings.S3_BUCKET_NAME
        self.region = region or settings.S3_REGION

        self._client = boto3.client(
            "s3",
            endpoint_url=self.endpoint_url,
            aws_access_key_id=self.access_key_id,
            aws_secret_access_key=self.secret_access_key,
            config=Config(signature_version="s3v4"),
            region_name=self.region,
        )

    def ensure_bucket_exists(self) -> None:
        """Create storage bucket if it does not already exist."""
        try:
            self._client.head_bucket(Bucket=self.bucket_name)
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code")
            if error_code in ("404", "NoSuchBucket"):
                self._client.create_bucket(Bucket=self.bucket_name)
            else:
                raise

    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """Strip directory paths and sanitize file name to safe characters."""
        base = filename.replace("\\", "/").split("/")[-1].strip()
        cleaned = re.sub(r"[^a-zA-Z0-9._-]", "_", base)
        return cleaned or "file.bin"

    def build_quarantine_key(
        self,
        institution_id: uuid.UUID,
        purpose: str,
        session_id: uuid.UUID,
        filename: str,
    ) -> str:
        """Generate quarantine storage key with institution scope."""
        safe_name = self.sanitize_filename(filename)
        return f"quarantine/{institution_id}/{purpose}/{session_id}/{safe_name}"

    def build_accepted_key(
        self,
        institution_id: uuid.UUID,
        purpose: str,
        hash_sha256: str,
        extension: str,
    ) -> str:
        """Generate immutable accepted key bound to SHA256 content hash."""
        ext = extension.strip()
        if ext and not ext.startswith("."):
            ext = f".{ext}"
        unique_suffix = uuid.uuid4().hex[:12]
        return f"accepted/{institution_id}/{purpose}/{hash_sha256}_{unique_suffix}{ext}"

    def generate_presigned_upload_url(
        self,
        storage_key: str,
        institution_id: uuid.UUID,
        expires_in: int = 900,
    ) -> str:
        """Generate presigned PUT URL for quarantine uploads (15-min default TTL)."""
        expected_prefix = f"quarantine/{institution_id}/"
        if not storage_key.startswith(expected_prefix):
            raise StorageSecurityError(
                f"Quarantine key '{storage_key}' does not match institution prefix '{expected_prefix}'"
            )

        url: str = self._client.generate_presigned_url(
            ClientMethod="put_object",
            Params={
                "Bucket": self.bucket_name,
                "Key": storage_key,
            },
            ExpiresIn=expires_in,
        )
        return url

    def promote_quarantine_to_accepted(
        self,
        quarantine_key: str,
        institution_id: uuid.UUID,
        purpose: str,
        extension: str,
        content_type: str | None = None,
        validated_data: bytes | None = None,
    ) -> tuple[str, str, int, bytes]:
        """Read quarantine bytes, verify tenant scope, compute hash, copy to accepted key, and purge quarantine."""
        expected_prefix = f"quarantine/{institution_id}/"
        if not quarantine_key.startswith(expected_prefix):
            raise StorageSecurityError(
                f"Quarantine key '{quarantine_key}' does not match tenant prefix '{expected_prefix}'"
            )

        data = validated_data if validated_data is not None else self.inspect_quarantine_object(
            quarantine_key, institution_id
        )[0]

        byte_size = len(data)
        hash_sha256 = hashlib.sha256(data).hexdigest()
        accepted_key = self.build_accepted_key(
            institution_id=institution_id,
            purpose=purpose,
            hash_sha256=hash_sha256,
            extension=extension,
        )

        extra_args: dict[str, Any] = {
            "Bucket": self.bucket_name,
            "Key": accepted_key,
            "Body": data,
            "Metadata": {
                "institution_id": str(institution_id),
                "sha256": hash_sha256,
                "purpose": purpose,
            },
        }
        if content_type:
            extra_args["ContentType"] = content_type

        # Save to immutable accepted storage
        self._client.put_object(**extra_args)

        # Purge quarantine object
        try:
            self._client.delete_object(Bucket=self.bucket_name, Key=quarantine_key)
        except Exception:  # noqa: S110
            pass

        return accepted_key, hash_sha256, byte_size, data

    def inspect_quarantine_object(
        self, quarantine_key: str, institution_id: uuid.UUID
    ) -> tuple[bytes, str | None, int]:
        """Read exact quarantine bytes and provider metadata without accepting them."""
        expected_prefix = f"quarantine/{institution_id}/"
        if not quarantine_key.startswith(expected_prefix):
            raise StorageSecurityError("Quarantine object is outside the institution namespace")
        try:
            response = self._client.get_object(Bucket=self.bucket_name, Key=quarantine_key)
            data: bytes = response["Body"].read()
        except ClientError as exc:
            raise FileNotFoundError(f"Quarantine file not found at key '{quarantine_key}'") from exc
        content_type = response.get("ContentType")
        return data, content_type, len(data)

    def store_accepted_bytes(
        self,
        data: bytes,
        institution_id: uuid.UUID,
        purpose: str,
        extension: str,
        content_type: str = "text/plain; charset=utf-8",
    ) -> tuple[str, str, int]:
        """Directly store server-validated or pasted bytes in accepted storage."""
        byte_size = len(data)
        hash_sha256 = hashlib.sha256(data).hexdigest()
        accepted_key = self.build_accepted_key(
            institution_id=institution_id,
            purpose=purpose,
            hash_sha256=hash_sha256,
            extension=extension,
        )

        self._client.put_object(
            Bucket=self.bucket_name,
            Key=accepted_key,
            Body=data,
            ContentType=content_type,
            Metadata={
                "institution_id": str(institution_id),
                "sha256": hash_sha256,
                "purpose": purpose,
            },
        )
        return accepted_key, hash_sha256, byte_size

    def get_object_bytes(self, storage_key: str, institution_id: uuid.UUID) -> bytes:
        """Retrieve object bytes with tenant isolation verification."""
        tenant_segment = f"/{institution_id}/"
        if tenant_segment not in storage_key:
            raise StorageSecurityError(
                f"Storage key '{storage_key}' does not contain expected tenant segment '{tenant_segment}'"
            )

        try:
            response = self._client.get_object(Bucket=self.bucket_name, Key=storage_key)
            data: bytes = response["Body"].read()
            return data
        except ClientError as e:
            raise FileNotFoundError(f"Object not found at key '{storage_key}': {e}") from e

    def generate_presigned_download_url(
        self,
        storage_key: str,
        institution_id: uuid.UUID,
        filename: str | None = None,
        expires_in: int = 300,
    ) -> str:
        """Generate presigned GET URL for accepted files (5-min default TTL)."""
        expected_prefix = f"accepted/{institution_id}/"
        if not storage_key.startswith(expected_prefix):
            raise StorageSecurityError(
                f"Storage key '{storage_key}' must begin with accepted prefix '{expected_prefix}'"
            )

        params: dict[str, Any] = {
            "Bucket": self.bucket_name,
            "Key": storage_key,
        }
        if filename:
            safe_fn = self.sanitize_filename(filename)
            params["ResponseContentDisposition"] = f'attachment; filename="{safe_fn}"'

        url: str = self._client.generate_presigned_url(
            ClientMethod="get_object",
            Params=params,
            ExpiresIn=expires_in,
        )
        return url

    def delete_object(self, storage_key: str, institution_id: uuid.UUID) -> None:
        """Delete an object with tenant check."""
        tenant_segment = f"/{institution_id}/"
        if tenant_segment not in storage_key:
            raise StorageSecurityError(
                f"Storage key '{storage_key}' does not match tenant '{tenant_segment}'"
            )
        self._client.delete_object(Bucket=self.bucket_name, Key=storage_key)


# Global storage service instance
storage_service = StorageService()

