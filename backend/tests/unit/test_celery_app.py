"""Worker registration tests for the executable Celery entry point."""

from placementos.workers.celery_app import celery_app


def test_source_extraction_task_is_registered():
    """Starting the documented worker must register the P03 extraction task."""
    celery_app.loader.import_default_modules()
    assert "placementos.workers.extract_source_text" in celery_app.tasks
