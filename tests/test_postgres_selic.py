import json
import os
from pathlib import Path

import pytest

from src.load import postgres_selic


def test_find_latest_raw_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Seleciona o JSON da Selic modificado mais recentemente."""

    older_file = tmp_path / "selic_20260710_100000.json"
    newer_file = tmp_path / "selic_20260711_100000.json"

    older_file.write_text(
        "{}",
        encoding="utf-8",
    )

    newer_file.write_text(
        "{}",
        encoding="utf-8",
    )

    os.utime(
        older_file,
        (1_000, 1_000),
    )

    os.utime(
        newer_file,
        (2_000, 2_000),
    )

    monkeypatch.setattr(
        postgres_selic,
        "RAW_DIRECTORY",
        tmp_path,
    )

    result = postgres_selic.find_latest_raw_file()

    assert result == newer_file


def test_read_payload_returns_valid_content(
    tmp_path: Path,
) -> None:
    """Lê corretamente um arquivo raw válido."""

    payload = {
        "series_code": 11,
        "records": [
            {
                "data": "10/07/2026",
                "valor": "0.055131",
            }
        ],
    }

    file_path = tmp_path / "selic_test.json"

    file_path.write_text(
        json.dumps(payload),
        encoding="utf-8",
    )

    result = postgres_selic.read_payload(file_path)

    assert result == payload
    assert len(result["records"]) == 1


def test_read_payload_rejects_missing_records(
    tmp_path: Path,
) -> None:
    """Reprova um JSON que não possua uma lista de registros."""

    file_path = tmp_path / "selic_invalid.json"

    file_path.write_text(
        json.dumps(
            {
                "series_code": 11,
                "records": "conteúdo inválido",
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="lista em 'records'",
    ):
        postgres_selic.read_payload(file_path)
    
