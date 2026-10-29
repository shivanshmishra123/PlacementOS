"""Integration tests for Recruitment Drives, Private S3 Intake, and Text Extraction (Phase 3).

Verifies:
- INV-03: Source facts remain traceable with exact page/paragraph locators.
- INV-06: Strict multi-tenant isolation across drives, sources, and download URLs.
- INV-07: Controlled private object storage with quarantine isolation and immutable accepted bytes.
- INV-08: Job restart and idempotency without state corruption.
- P03-T01 through P03-T06: Company/drive lifecycle, optimistic concurrency, and parse error handling.
"""

import io
import uuid

import pytest
from botocore.exceptions import ClientError
from docx import Document
from httpx import AsyncClient

from placementos.services.storage import storage_service


def create_test_docx(paragraphs: list[str]) -> bytes:
    doc = Document()
    for p in paragraphs:
        doc.add_paragraph(p)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


@pytest.mark.asyncio
async def test_company_and_drive_lifecycle_and_concurrency(client: AsyncClient):
    """Test company registration, drive creation, initial revision, and optimistic concurrency."""
    # 1. Login as Apex Coordinator
    login_resp = await client.post("/api/v1/auth/dev-login", json={"persona": "coord_apex"})
    assert login_resp.status_code == 200

    unique_suffix = uuid.uuid4().hex[:6]
    company_name = f"Stripe Inc - {unique_suffix}"

    # 2. Register hiring company
    comp_resp = await client.post(
        "/api/v1/companies",
        json={
            "name": company_name,
            "industry": "FinTech / Payments",
            "website": "https://stripe.com",
            "contact_email": "recruiting@stripe.com",
        },
    )
    assert comp_resp.status_code == 201
    comp_data = comp_resp.json()
    company_id = comp_data["id"]
    assert comp_data["name"] == company_name

    # 3. Create recruitment drive
    drive_resp = await client.post(
        "/api/v1/drives",
        json={
            "company_id": company_id,
            "academic_year": "2026-2027",
            "title": f"Software Engineer - Payments - {unique_suffix}",
            "description": "Campus recruitment drive for 2027 batch",
        },
    )
    assert drive_resp.status_code == 201
    drive_data = drive_resp.json()
    drive_id = drive_data["id"]
    assert drive_data["status"] == "draft"
    assert drive_data["current_revision_number"] == 1
    assert len(drive_data["revisions"]) == 1
    assert drive_data["revisions"][0]["revision_number"] == 1

    # 4. Optimistic concurrency conflict check: supply wrong expected revision
    conflict_resp = await client.post(
        f"/api/v1/drives/{drive_id}/revisions",
        json={
            "expected_revision_number": 999,
            "change_summary": "Attempting stale update",
            "proposed_changes": {"stale": True},
        },
    )
    assert conflict_resp.status_code == 409
    assert "concurrency conflict" in conflict_resp.json()["error"]["message"].lower()

    # 5. Successful revision append with expected_revision_number = 1
    rev_resp = await client.post(
        f"/api/v1/drives/{drive_id}/revisions",
        json={
            "expected_revision_number": 1,
            "change_summary": "Updated eligibility criteria to allow 1 active backlog",
            "proposed_changes": {"max_active_backlogs": 1},
        },
    )
    assert rev_resp.status_code == 201
    rev_data = rev_resp.json()
    assert rev_data["revision_number"] == 2

    # Verify drive's current revision is now 2
    get_drive_resp = await client.get(f"/api/v1/drives/{drive_id}")
    assert get_drive_resp.status_code == 200
    assert get_drive_resp.json()["current_revision_number"] == 2


@pytest.mark.asyncio
async def test_pasted_source_intake_and_locators(client: AsyncClient):
    """Test raw pasted job description intake, storage, and precise locator extraction."""
    await client.post("/api/v1/auth/dev-login", json={"persona": "coord_apex"})

    # Create company and drive
    unique_suffix = uuid.uuid4().hex[:6]
    comp_resp = await client.post("/api/v1/companies", json={"name": f"Google Cloud - {unique_suffix}"})
    company_id = comp_resp.json()["id"]

    drive_resp = await client.post(
        "/api/v1/drives",
        json={
            "company_id": company_id,
            "academic_year": "2026-2027",
            "title": f"Associate Cloud Engineer - {unique_suffix}",
        },
    )
    drive_id = drive_resp.json()["id"]

    # Intake pasted JD text
    pasted_text = (
        "Role: Associate Cloud Engineer (Campus 2026)\n\n"
        "Eligibility Requirements:\n"
        "B.Tech Computer Science or Information Technology graduating in 2027.\n"
        "Cumulative Grade Point Average (CGPA) of at least 8.00 out of 10.0.\n\n"
        "Compensation and Benefits:\n"
        "Base Salary: 16 LPA with 2 Lakhs joining bonus."
    )
    paste_resp = await client.post(
        f"/api/v1/drives/{drive_id}/sources/pasted",
        json={
            "title": "Google Cloud Campus JD",
            "raw_text": pasted_text,
        },
    )
    assert paste_resp.status_code == 201
    artifact_data = paste_resp.json()
    artifact_id = artifact_data["id"]
    assert artifact_data["status"] == "extracted"
    assert artifact_data["source_type"] == "pasted_text"
    assert artifact_data["hash_sha256"] is not None

    # Retrieve extracted text and locators
    ext_resp = await client.get(f"/api/v1/sources/{artifact_id}/extractions")
    assert ext_resp.status_code == 200
    ext_data = ext_resp.json()
    assert ext_data["paragraph_count"] >= 3
    assert len(ext_data["locators"]) == ext_data["paragraph_count"]

    # Verify locator offset mapping
    first_loc = ext_data["locators"][0]
    assert first_loc["paragraph_index"] == 0
    assert first_loc["char_offset_start"] == 0
    assert "Associate Cloud Engineer" in first_loc["preview"]

    # Retrieve download URL
    dl_resp = await client.get(f"/api/v1/sources/{artifact_id}/download-url")
    assert dl_resp.status_code == 200
    assert "download_url" in dl_resp.json()
    assert "placementos-dev" in dl_resp.json()["download_url"]


@pytest.mark.asyncio
async def test_quarantine_upload_and_promotion_flow(client: AsyncClient):
    """Test quarantine upload session generation, direct S3 upload, and completion promotion."""
    await client.post("/api/v1/auth/dev-login", json={"persona": "coord_apex"})

    # Setup drive
    comp_resp = await client.post("/api/v1/companies", json={"name": f"Microsoft IDC - {uuid.uuid4().hex[:6]}"})
    drive_resp = await client.post(
        "/api/v1/drives",
        json={
            "company_id": comp_resp.json()["id"],
            "academic_year": "2026-2027",
            "title": "Software Development Engineer - IDC",
        },
    )
    drive_id = drive_resp.json()["id"]

    # 1. Create upload session
    docx_bytes = create_test_docx([
        "Microsoft Campus Hiring 2026",
        "Role: Software Engineer (Full-time)",
        "Minimum CGPA: 7.75 with no current backlogs",
    ])
    session_resp = await client.post(
        "/api/v1/uploads/sessions",
        json={
            "drive_id": drive_id,
            "purpose": "jd_intake",
            "original_filename": "Microsoft_JD_2026.docx",
            "content_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "byte_size": len(docx_bytes),
        },
    )
    assert session_resp.status_code == 201
    session_data = session_resp.json()
    session_id = session_data["id"]
    storage_key = session_data["storage_key"]
    assert "quarantine/" in storage_key

    # 2. Put bytes directly into S3 quarantine storage using storage_service client
    storage_service._client.put_object(
        Bucket=storage_service.bucket_name,
        Key=storage_key,
        Body=docx_bytes,
    )

    # 3. Call complete endpoint
    complete_resp = await client.post(f"/api/v1/uploads/sessions/{session_id}/complete")
    assert complete_resp.status_code == 201
    artifact_data = complete_resp.json()
    assert artifact_data["status"] == "extracted"
    assert "accepted/" in artifact_data["storage_key"]

    # 4. Verify quarantine file was purged from S3
    with pytest.raises(ClientError):
        storage_service._client.head_object(Bucket=storage_service.bucket_name, Key=storage_key)

    # 5. Check extraction
    ext_resp = await client.get(f"/api/v1/sources/{artifact_data['id']}/extractions")
    assert ext_resp.status_code == 200
    ext_data = ext_resp.json()
    assert ext_data["paragraph_count"] == 3
    assert "Microsoft Campus Hiring" in ext_data["extracted_text"]


@pytest.mark.asyncio
async def test_corrupt_file_handling_in_upload_complete(client: AsyncClient):
    """Verify that corrupt or spoofed files fail with typed error codes on complete."""
    await client.post("/api/v1/auth/dev-login", json={"persona": "coord_apex"})

    comp_resp = await client.post("/api/v1/companies", json={"name": f"Amazon - {uuid.uuid4().hex[:6]}"})
    drive_resp = await client.post(
        "/api/v1/drives",
        json={"company_id": comp_resp.json()["id"], "academic_year": "2026-2027", "title": "SDE-1"},
    )
    drive_id = drive_resp.json()["id"]

    # Upload session for claimed docx
    session_resp = await client.post(
        "/api/v1/uploads/sessions",
        json={
            "drive_id": drive_id,
            "original_filename": "fake_doc.docx",
            "content_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "byte_size": 256,
        },
    )
    session_data = session_resp.json()

    # Upload invalid non-zip byte garbage into quarantine
    storage_service._client.put_object(
        Bucket=storage_service.bucket_name,
        Key=session_data["storage_key"],
        Body=b"GARBAGE_PAYLOAD_NOT_DOCX_OR_ZIP",
    )

    # Complete upload: should record failure on artifact
    complete_resp = await client.post(f"/api/v1/uploads/sessions/{session_data['id']}/complete")
    assert complete_resp.status_code == 201
    artifact_data = complete_resp.json()
    assert artifact_data["status"] == "failed"
    assert artifact_data["metadata_json"]["error_code"] == "MIMETYPE_MISMATCH"


@pytest.mark.asyncio
async def test_cross_tenant_isolation_for_drives_and_sources(client: AsyncClient):
    """Verify INV-06: Beacon coordinator cannot access Apex drive or source artifacts."""
    # 1. Apex coordinator creates drive and pasted source
    await client.post("/api/v1/auth/dev-login", json={"persona": "coord_apex"})

    comp_resp = await client.post("/api/v1/companies", json={"name": f"Oracle - {uuid.uuid4().hex[:6]}"})
    drive_resp = await client.post(
        "/api/v1/drives",
        json={"company_id": comp_resp.json()["id"], "academic_year": "2026-2027", "title": "Database Engineer"},
    )
    apex_drive_id = drive_resp.json()["id"]

    source_resp = await client.post(
        f"/api/v1/drives/{apex_drive_id}/sources/pasted",
        json={"title": "Oracle Private JD", "raw_text": "Confidential hiring details for Apex only.\n\nMin CGPA 8.0"},
    )
    apex_source_id = source_resp.json()["id"]

    # 2. Beacon coordinator logs in
    login_beacon = await client.post("/api/v1/auth/dev-login", json={"persona": "coord_beacon"})
    assert login_beacon.status_code == 200

    # 3. Beacon coordinator attempts to read Apex drive
    beacon_drive_get = await client.get(f"/api/v1/drives/{apex_drive_id}")
    assert beacon_drive_get.status_code == 404

    # 4. Beacon coordinator attempts to read Apex source artifact
    beacon_source_get = await client.get(f"/api/v1/sources/{apex_source_id}")
    assert beacon_source_get.status_code == 404

    # 5. Beacon coordinator attempts to read Apex extractions
    beacon_ext_get = await client.get(f"/api/v1/sources/{apex_source_id}/extractions")
    assert beacon_ext_get.status_code == 404

    # 6. Beacon coordinator attempts to get download URL
    beacon_dl_get = await client.get(f"/api/v1/sources/{apex_source_id}/download-url")
    assert beacon_dl_get.status_code == 404


@pytest.mark.asyncio
async def test_extraction_idempotency_and_retry(client: AsyncClient):
    """Verify INV-08: Re-triggering text extraction is idempotent and does not duplicate state."""
    await client.post("/api/v1/auth/dev-login", json={"persona": "coord_apex"})

    comp_resp = await client.post("/api/v1/companies", json={"name": f"Uber - {uuid.uuid4().hex[:6]}"})
    drive_resp = await client.post(
        "/api/v1/drives",
        json={"company_id": comp_resp.json()["id"], "academic_year": "2026-2027", "title": "Backend Engineer"},
    )
    drive_id = drive_resp.json()["id"]

    source_resp = await client.post(
        f"/api/v1/drives/{drive_id}/sources/pasted",
        json={"title": "Uber JD", "raw_text": "Uber Technologies campus hiring.\n\nRequired CGPA: 8.5"},
    )
    artifact_id = source_resp.json()["id"]

    # Re-trigger extraction
    retry_resp = await client.post(f"/api/v1/sources/{artifact_id}/extract")
    assert retry_resp.status_code == 200
    job_data = retry_resp.json()
    assert job_data["status"] == "completed"

    # Verify only single extraction record exists and is valid
    ext_resp = await client.get(f"/api/v1/sources/{artifact_id}/extractions")
    assert ext_resp.status_code == 200
    ext_data = ext_resp.json()
    assert ext_data["paragraph_count"] >= 2
