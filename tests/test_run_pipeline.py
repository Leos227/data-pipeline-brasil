from pathlib import Path
from typing import Any

import pytest

import src.pipeline.run_pipeline as pipeline_module


class FakeConnection:
    """Simula o contexto de conexão do pipeline."""

    def __enter__(self) -> "FakeConnection":
        return self

    def __exit__(
        self,
        exc_type: Any,
        exc_value: Any,
        traceback: Any,
    ) -> None:
        return None


def configure_successful_pipeline(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    calls: list[str],
) -> None:
    """Substitui dependências externas por simulações."""

    payload = {
        "record_count": 2,
        "records": [
            {
                "data": "10/07/2026",
                "valor": "0.055131",
            },
            {
                "data": "11/07/2026",
                "valor": "0.055131",
            },
        ],
    }

    def fake_extract(days: int) -> dict[str, Any]:
        calls.append(f"extract:{days}")
        return payload

    def fake_save(data: dict[str, Any]) -> Path:
        calls.append("save")
        return tmp_path / "selic_test.json"

    def fake_create_structure(connection: Any) -> None:
        calls.append("create_structure")

    def fake_load(
        connection: Any,
        payload: dict[str, Any],
    ) -> int:
        calls.append("load")
        return 2

    def fake_transform(connection: Any) -> None:
        calls.append("transform")

    monkeypatch.setattr(
        pipeline_module,
        "extract_selic",
        fake_extract,
    )

    monkeypatch.setattr(
        pipeline_module,
        "save_raw_data",
        fake_save,
    )

    monkeypatch.setattr(
        pipeline_module,
        "get_connection",
        lambda: FakeConnection(),
    )

    monkeypatch.setattr(
        pipeline_module,
        "create_database_structure",
        fake_create_structure,
    )

    monkeypatch.setattr(
        pipeline_module,
        "load_selic",
        fake_load,
    )

    monkeypatch.setattr(
        pipeline_module,
        "execute_transformations",
        fake_transform,
    )


def test_pipeline_executes_all_steps(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Executa todas as etapas na ordem esperada."""

    calls: list[str] = []

    configure_successful_pipeline(
        monkeypatch,
        tmp_path,
        calls,
    )

    monkeypatch.setattr(
        pipeline_module,
        "run_quality_checks",
        lambda: calls.append("quality") or [],
    )

    pipeline_module.run_pipeline(days=10)

    assert calls == [
        "extract:10",
        "save",
        "create_structure",
        "load",
        "transform",
        "quality",
    ]


def test_pipeline_stops_when_quality_fails(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Interrompe o pipeline quando uma validação reprova."""

    calls: list[str] = []

    configure_successful_pipeline(
        monkeypatch,
        tmp_path,
        calls,
    )

    monkeypatch.setattr(
        pipeline_module,
        "run_quality_checks",
        lambda: ["Sem datas duplicadas"],
    )

    with pytest.raises(
        RuntimeError,
        match="Qualidade dos dados reprovada",
    ):
        pipeline_module.run_pipeline()
