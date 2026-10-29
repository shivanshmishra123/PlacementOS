"""Unit tests for private S3 storage service, isolation, and URL generation."""

import uuid

import pytest

from placementos.services.storage import StorageSecurityError, StorageService


class TestStorageService:
    def setup_method(self):
        self.service = StorageService()

    def test_sanitize_filename(self):
        assert self.service.sanitize_filename("test/path/to/my_file.pdf") == "my_file.pdf"
        assert self.service.sanitize_filename("..\\..\\malicious.exe") == "malicious.exe"
        assert self.service.sanitize_filename("spaces & weird characters?.docx") == "spaces___weird_characters_.docx"

    def test_quarantine_key_structure(self):
        inst_id = uuid.uuid4()
        session_id = uuid.uuid4()
        key = self.service.build_quarantine_key(inst_id, "jd_intake", session_id, "jd.pdf")
        assert key.startswith(f"quarantine/{inst_id}/jd_intake/{session_id}/jd.pdf")

    def test_accepted_key_structure(self):
        inst_id = uuid.uuid4()
        key = self.service.build_accepted_key(inst_id, "jd_intake", "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855", ".pdf")
        assert key.startswith(f"accepted/{inst_id}/jd_intake/e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855_")
        assert key.endswith(".pdf")

    def test_quarantine_presigned_url_tenant_violation(self):
        inst_a = uuid.uuid4()
        inst_b = uuid.uuid4()
        key_a = f"quarantine/{inst_a}/jd_intake/{uuid.uuid4()}/file.pdf"

        # Attempting to sign key of inst_a with inst_b
        with pytest.raises(StorageSecurityError):
            self.service.generate_presigned_upload_url(key_a, inst_b)

    def test_download_presigned_url_quarantine_rejection(self):
        inst = uuid.uuid4()
        quarantine_key = f"quarantine/{inst}/jd_intake/{uuid.uuid4()}/file.pdf"

        # Quarantine keys must not be downloadable via download url method
        with pytest.raises(StorageSecurityError):
            self.service.generate_presigned_download_url(quarantine_key, inst)

    def test_download_presigned_url_tenant_isolation(self):
        inst_a = uuid.uuid4()
        inst_b = uuid.uuid4()
        accepted_key_a = f"accepted/{inst_a}/jd_intake/hash_123.pdf"

        # Tenant B cannot request download URL for Tenant A's file
        with pytest.raises(StorageSecurityError):
            self.service.generate_presigned_download_url(accepted_key_a, inst_b)

