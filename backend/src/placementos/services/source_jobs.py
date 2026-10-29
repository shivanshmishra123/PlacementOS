"""Source Extraction Domain Job Service.

Coordinates synchronous and asynchronous text extraction jobs, updates domain state,
records fine-grained locators, and guarantees idempotency on job retries.
"""

from __future__ import annotations

import hashlib
import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from placementos.core.database import async_session_maker
from placementos.models.storage import DomainJob, SourceArtifact, TextExtraction
from placementos.services.parsers import DocumentScanner, ParseError, TextExtractor
from placementos.services.storage import storage_service

logger = logging.getLogger(__name__)


class SourceJobService:
    """Orchestrates document extraction jobs with durable state tracking and idempotency."""

    @classmethod
    async def create_extraction_job(
        cls,
        session: AsyncSession,
        source_artifact: SourceArtifact,
    ) -> DomainJob:
        """Create or return existing queued DomainJob for source extraction."""
        operation_key = f"extract:{source_artifact.id}"
        stmt = select(DomainJob).where(
            DomainJob.institution_id == source_artifact.institution_id,
            DomainJob.operation_key == operation_key,
        )
        existing = (await session.execute(stmt)).scalar_one_or_none()

        if existing:
            return existing

        job = DomainJob(
            institution_id=source_artifact.institution_id,
            job_kind="extract_source_text",
            resource_type="source_artifact",
            resource_id=source_artifact.id,
            operation_key=operation_key,
            status="queued",
            attempts=0,
            max_attempts=3,
        )
        session.add(job)
        await session.flush()
        return job

    @classmethod
    async def run_extraction(
        cls,
        source_artifact_id: uuid.UUID,
        institution_id: uuid.UUID,
        session: AsyncSession | None = None,
    ) -> TextExtraction:
        """Execute text extraction synchronously or inside a Celery task. Idempotent."""
        if session is not None:
            return await cls._execute_extraction(session, source_artifact_id, institution_id)

        async with async_session_maker() as new_session:
            async with new_session.begin():
                return await cls._execute_extraction(new_session, source_artifact_id, institution_id)

    @classmethod
    async def _execute_extraction(
        cls,
        session: AsyncSession,
        source_artifact_id: uuid.UUID,
        institution_id: uuid.UUID,
    ) -> TextExtraction:
        """Internal execution with isolation checks, scanning, locator generation, and state updates."""
        # Check source artifact
        stmt = (
            select(SourceArtifact)
            .where(
                SourceArtifact.id == source_artifact_id,
                SourceArtifact.institution_id == institution_id,
            )
            .with_for_update()
        )
        artifact = (await session.execute(stmt)).scalar_one_or_none()
        if not artifact:
            raise ValueError(f"SourceArtifact '{source_artifact_id}' not found for institution '{institution_id}'")

        # Idempotency check: if already extracted, return existing extraction
        ext_stmt = select(TextExtraction).where(TextExtraction.source_artifact_id == source_artifact_id)
        existing_extraction = (await session.execute(ext_stmt)).scalar_one_or_none()
        if existing_extraction and existing_extraction.status == "completed":
            logger.info("Extraction already completed for artifact %s, returning cached result", source_artifact_id)
            return existing_extraction

        # Fetch or initialize DomainJob
        operation_key = f"extract:{source_artifact_id}"
        job_stmt = select(DomainJob).where(
            DomainJob.institution_id == institution_id,
            DomainJob.operation_key == operation_key,
        ).with_for_update()
        job = (await session.execute(job_stmt)).scalar_one_or_none()
        if not job:
            job = DomainJob(
                institution_id=institution_id,
                job_kind="extract_source_text",
                resource_type="source_artifact",
                resource_id=source_artifact_id,
                operation_key=operation_key,
                status="queued",
                attempts=0,
                max_attempts=3,
            )
            session.add(job)

        job.status = "processing"
        job.attempts += 1
        await session.flush()

        try:
            # 1. Fetch bytes from private object store
            data = storage_service.get_object_bytes(artifact.object_key, institution_id)

            # 2. Extract file extension from filename or media_type
            filename = artifact.file_name or "file.txt"
            ext = filename.split(".")[-1] if "." in filename else "txt"
            canonical_type = DocumentScanner.scan_bytes(data, ext)

            # 3. Extract text and compute precise locators
            result = TextExtractor.extract(data, canonical_type)
            text_hash = hashlib.sha256(result.extracted_text.encode("utf-8")).hexdigest()

            # 4. Save TextExtraction record
            if existing_extraction:
                extraction = existing_extraction
                extraction.extracted_text = result.extracted_text
                extraction.text_hash_sha256 = text_hash
                extraction.locators = [loc.to_dict() for loc in result.locators]
                extraction.page_count = result.page_count
                extraction.parser_version = result.parser_version
                extraction.is_empty_or_scanned = result.is_empty_or_scanned
                extraction.status = "completed"
                extraction.error_message = None
            else:
                extraction = TextExtraction(
                    source_artifact_id=artifact.id,
                    institution_id=institution_id,
                    parser_version=result.parser_version,
                    extraction_method=f"{canonical_type}_extractor",
                    text_hash_sha256=text_hash,
                    extracted_text=result.extracted_text,
                    page_count=result.page_count,
                    is_empty_or_scanned=result.is_empty_or_scanned,
                    status="completed",
                    error_message=None,
                    locators=[loc.to_dict() for loc in result.locators],
                )
                session.add(extraction)

            artifact.acceptance_status = "accepted"
            artifact.scan_status = "clean"

            job.status = "completed"
            job.error_details = None
            await session.flush()
            return extraction

        except ParseError as exc:
            artifact.acceptance_status = "rejected"
            artifact.scan_status = "suspicious"

            # Create or update failed TextExtraction
            if existing_extraction:
                existing_extraction.status = "failed"
                existing_extraction.error_message = exc.message
            else:
                failed_extraction = TextExtraction(
                    source_artifact_id=artifact.id,
                    institution_id=institution_id,
                    parser_version="1.0.0",
                    extraction_method="unknown",
                    text_hash_sha256="failed",
                    extracted_text="",
                    page_count=0,
                    is_empty_or_scanned=False,
                    status="failed",
                    error_message=exc.message,
                    locators=[],
                )
                session.add(failed_extraction)

            job.status = "failed"
            job.error_details = {"error_code": exc.code, "error_message": exc.message}
            await session.flush()
            raise

        except Exception as exc:
            artifact.acceptance_status = "rejected"
            job.status = "failed"
            job.error_details = {"error_code": "EXTRACTION_FAILED", "error_message": str(exc)}
            await session.flush()
            raise
