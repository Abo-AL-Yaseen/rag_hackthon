import json
from pathlib import Path

import pytest

from backend.catalog import load_catalog


def test_rejects_unverified_catalog(tmp_path: Path):
    path = tmp_path / "programs.json"
    path.write_text(
        json.dumps({"catalog_version": "1.0.0", "verified": False, "programs": []}),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="verified"):
        load_catalog(path)


def test_rejects_fabricated_empty_document_ids(tmp_path: Path):
    path = tmp_path / "programs.json"
    path.write_text(
        json.dumps(
            {
                "catalog_version": "1.0.0",
                "verified": True,
                "programs": [
                    {
                        "program_id": "x",
                        "name": "X",
                        "plan_version": "1",
                        "document_ids": [],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="document_ids"):
        load_catalog(path)
