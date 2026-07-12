import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import requests


SERIES_CODE = 11
BASE_URL = (
    f"https://api.bcb.gov.br/dados/serie/"
    f"bcdata.sgs.{SERIES_CODE}/dados"
)


def extract_selic(days: int = 30) -> dict[str, Any]:
    """Extrai os dados mais recentes da série diária da Selic."""

    end_date = date.today()
    start_date = end_date - timedelta(days=days)

    params = {
        "formato": "json",
        "dataInicial": start_date.strftime("%d/%m/%Y"),
        "dataFinal": end_date.strftime("%d/%m/%Y"),
    }

    response = requests.get(
        BASE_URL,
        params=params,
        timeout=30,
    )
    response.raise_for_status()

    records = response.json()

    if not isinstance(records, list):
        raise ValueError("A resposta da API não contém uma lista de registros.")

    return {
        "source": "Banco Central do Brasil - SGS",
        "series_code": SERIES_CODE,
        "series_name": "Taxa de juros - Selic",
        "extracted_at_utc": datetime.now(timezone.utc).isoformat(),
        "period": {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
        },
        "record_count": len(records),
        "records": records,
    }


def save_raw_data(payload: dict[str, Any]) -> Path:
    """Salva a resposta sem transformações na camada raw."""

    project_root = Path(__file__).resolve().parents[2]
    output_directory = project_root / "data" / "raw"
    output_directory.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_directory / f"selic_{timestamp}.json"

    output_file.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return output_file


def main() -> None:
    try:
        payload = extract_selic()
        output_file = save_raw_data(payload)

        print("Ingestão concluída com sucesso.")
        print(f"Registros extraídos: {payload['record_count']}")
        print(f"Arquivo criado: {output_file}")

    except requests.RequestException as error:
        print(f"Erro ao acessar a API do Banco Central: {error}")
        raise SystemExit(1) from error

    except (ValueError, OSError) as error:
        print(f"Erro ao processar ou salvar os dados: {error}")
        raise SystemExit(1) from error


if __name__ == "__main__":
    main()
