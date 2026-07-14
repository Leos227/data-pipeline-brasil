from typing import Any

import pytest

from src.extract import bcb_sgs


class FakeResponse:
    """Simula uma resposta HTTP da API."""

    def __init__(self, payload: Any) -> None:
        self.payload = payload

    def raise_for_status(self) -> None:
        """Simula uma resposta HTTP bem-sucedida."""

    def json(self) -> Any:
        return self.payload


def test_extract_selic_returns_expected_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verifica a estrutura produzida pela extração."""

    records = [
        {
            "data": "10/07/2026",
            "valor": "0.055131",
        },
        {
            "data": "11/07/2026",
            "valor": "0.055131",
        },
    ]

    captured_request: dict[str, Any] = {}

    def fake_get(
        url: str,
        params: dict[str, str],
        timeout: int,
    ) -> FakeResponse:
        captured_request["url"] = url
        captured_request["params"] = params
        captured_request["timeout"] = timeout

        return FakeResponse(records)

    monkeypatch.setattr(
        bcb_sgs.requests,
        "get",
        fake_get,
    )

    result = bcb_sgs.extract_selic(days=30)

    assert result["series_code"] == 11
    assert result["record_count"] == 2
    assert result["records"] == records
    assert result["source"] == "Banco Central do Brasil - SGS"

    assert "extracted_at_utc" in result
    assert "start_date" in result["period"]
    assert "end_date" in result["period"]

    assert captured_request["timeout"] == 30
    assert captured_request["params"]["formato"] == "json"
    assert "bcdata.sgs.11" in captured_request["url"]


def test_extract_selic_rejects_invalid_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Reprova respostas que não contenham uma lista."""

    def fake_get(
        url: str,
        params: dict[str, str],
        timeout: int,
    ) -> FakeResponse:
        return FakeResponse(
            {
                "erro": "resposta inválida",
            }
        )

    monkeypatch.setattr(
        bcb_sgs.requests,
        "get",
        fake_get,
    )

    with pytest.raises(
        ValueError,
        match="lista de registros",
    ):
        bcb_sgs.extract_selic()
