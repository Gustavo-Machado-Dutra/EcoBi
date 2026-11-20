from __future__ import annotations

from pathlib import Path
from typing import Dict

from fastapi.testclient import TestClient

from backend import database


def test_failed_reupload_with_existing_filename_preserves_dataset_file(
    client: TestClient,
    auth_headers: Dict[str, str],
    tmp_path: Path,
) -> None:
    project_response = client.post(
        "/api/projects",
        json={"name": "QA Upload Recovery", "sector": "Varejo", "currency": "BRL"},
        headers=auth_headers,
    )
    assert project_response.status_code == 201
    project_id = project_response.json()["id"]

    valid_upload = tmp_path / "valid.csv"
    valid_upload.write_bytes(b"amount,date\n10,2026-01-01\n")
    with valid_upload.open("rb") as dataset_file:
        upload_response = client.post(
            f"/api/projects/{project_id}/datasets/upload",
            files={"file": ("ledger.csv", dataset_file, "text/csv")},
            headers=auth_headers,
        )
    assert upload_response.status_code == 201
    dataset_id = upload_response.json()["dataset"]["id"]
    stored_record = database.get_dataset(dataset_id)
    assert stored_record is not None
    stored_path = Path(stored_record["storage_path"])
    original_bytes = stored_path.read_bytes()

    repeated_valid_upload = tmp_path / "valid-repeat.csv"
    repeated_valid_upload.write_bytes(b"amount,date\n20,2026-02-01\n")
    with repeated_valid_upload.open("rb") as dataset_file:
        repeated_response = client.post(
            f"/api/projects/{project_id}/datasets/upload",
            files={"file": ("ledger.csv", dataset_file, "text/csv")},
            headers=auth_headers,
        )
    assert repeated_response.status_code == 201
    repeated_id = repeated_response.json()["dataset"]["id"]
    repeated_record = database.get_dataset(repeated_id)
    assert repeated_record is not None
    repeated_path = Path(repeated_record["storage_path"])
    repeated_bytes = repeated_path.read_bytes()
    assert repeated_path != stored_path

    invalid_upload = tmp_path / "invalid.csv"
    invalid_upload.write_bytes(b'amount,date\n10,2026-01-01\n"unterminated')
    with invalid_upload.open("rb") as dataset_file:
        rejected_response = client.post(
            f"/api/projects/{project_id}/datasets/upload",
            files={"file": ("ledger.csv", dataset_file, "text/csv")},
            headers=auth_headers,
        )

    assert rejected_response.status_code == 400
    assert stored_path.is_file()
    assert stored_path.read_bytes() == original_bytes
    assert repeated_path.is_file()
    assert repeated_path.read_bytes() == repeated_bytes
    remaining_datasets = database.list_datasets(project_id)
    assert {dataset["id"] for dataset in remaining_datasets} == {dataset_id, repeated_id}
    assert {path.resolve() for path in stored_path.parent.iterdir()} == {
        stored_path.resolve(),
        repeated_path.resolve(),
    }



def test_api_journey_persists_project_import_quality_analysis_validation_and_powerbi(
    client: TestClient,
    auth_headers: Dict[str, str],
    sample_paths: Dict[str, Path],
) -> None:
    project_response = client.post(
        "/api/projects",
        json={"name": "QA API E2E", "sector": "Varejo", "currency": "BRL"},
        headers=auth_headers,
    )
    assert project_response.status_code == 201
    project_id = project_response.json()["id"]

    with sample_paths["piloto"].open("rb") as dataset_file:
        upload_response = client.post(
            f"/api/projects/{project_id}/datasets/upload",
            files={"file": ("synthetic-pilot.csv", dataset_file, "text/csv")},
            headers=auth_headers,
        )
    assert upload_response.status_code == 201
    dataset_id = upload_response.json()["dataset"]["id"]
    assert upload_response.json()["quality_report"]["dataset_id"] == dataset_id

    quality_response = client.get(f"/api/projects/{project_id}/quality", headers=auth_headers)
    assert quality_response.status_code == 200
    assert quality_response.json()["dataset_id"] == dataset_id

    assistant_response = client.post(
        f"/api/projects/{project_id}/assistant",
        json={"message": "Resuma a qualidade dos dados do projeto.", "dataset_id": dataset_id},
        headers=auth_headers,
    )
    assert assistant_response.status_code == 200
    assert assistant_response.json()["execution_mode"] in ("deterministic_local_fallback", "ollama_tool_calling")

    analysis_response = client.post(
        f"/api/projects/{project_id}/analyze/financial-esg",
        json={"dataset_id": dataset_id},
        headers=auth_headers,
    )
    assert analysis_response.status_code == 200
    analysis_id = analysis_response.json()["analysis_id"]
    assert analysis_response.json()["validation"]["analysis_id"] == analysis_id

    predictive_response = client.post(
        f"/api/projects/{project_id}/analyze/predictive",
        json={
            "dataset_id": dataset_id,
            "target_column": "receita_bruta",
            "model_type": "ridge",
            "forecast_horizon": 3,
        },
        headers=auth_headers,
    )
    assert predictive_response.status_code == 200
    predictive_id = predictive_response.json()["analysis_id"]
    assert predictive_response.json()["validation"]["analysis_id"] == predictive_id

    simulation_response = client.post(
        f"/api/projects/{project_id}/simulate",
        json={"base_analysis_id": analysis_id, "cost_reduction_pct": 5.0, "electricity_reduction_pct": 10.0},
        headers=auth_headers,
    )
    assert simulation_response.status_code == 200
    simulation_id = simulation_response.json()["analysis_id"]
    assert simulation_response.json()["observed_impacts"]["status"] == "not_observed_yet"

    project_detail = client.get(f"/api/projects/{project_id}", headers=auth_headers)
    assert project_detail.status_code == 200
    assert any(item["id"] == dataset_id for item in project_detail.json()["datasets"])
    persisted_analysis_ids = {item["id"] for item in project_detail.json()["analyses"]}
    assert {analysis_id, predictive_id, simulation_id}.issubset(persisted_analysis_ids)

    validations = client.get(f"/api/projects/{project_id}/validations", headers=auth_headers)
    assert validations.status_code == 200
    persisted_validation_analysis_ids = {item["analysis_id"] for item in validations.json()["validations"]}
    assert {analysis_id, predictive_id, simulation_id}.issubset(persisted_validation_analysis_ids)

    second_project_response = client.post(
        "/api/projects",
        json={"name": "QA API E2E Second Project", "sector": "Varejo", "currency": "BRL"},
        headers=auth_headers,
    )
    assert second_project_response.status_code == 201
    second_project_id = second_project_response.json()["id"]
    with open(sample_paths["piloto"], "rb") as sample_file:
        second_upload = client.post(
            f"/api/projects/{second_project_id}/datasets/upload",
            files={"file": ("qa_second_project.csv", sample_file, "text/csv")},
            headers=auth_headers,
        )
    assert second_upload.status_code == 201
    second_dataset_id = second_upload.json()["dataset"]["id"]
    second_analysis = client.post(
        f"/api/projects/{second_project_id}/analyze/financial-esg",
        json={"dataset_id": second_dataset_id},
        headers=auth_headers,
    )
    assert second_analysis.status_code == 200

    dashboard_response = client.get("/api/multiproject/overview", headers=auth_headers)
    assert dashboard_response.status_code == 200
    dashboard_data = dashboard_response.json()
    dashboard_projects = {item["project_id"]: item for item in dashboard_data["projects"]}
    assert dashboard_projects[project_id]["has_data"] is True
    assert dashboard_projects[second_project_id]["has_data"] is True
    assert dashboard_data["accessible_projects_count"] == 2
    totals = dashboard_data["consolidated_totals"]
    expected_revenue = (
        analysis_response.json()["financial_kpis"]["receita_bruta_total"]
        + second_analysis.json()["financial_kpis"]["receita_bruta_total"]
    )
    assert totals["receita_bruta_total"] == round(expected_revenue, 2)

    export_response = client.post(
        f"/api/projects/{project_id}/powerbi/generate",
        json={"analysis_ids": [analysis_id, predictive_id, simulation_id], "report_title": "QA API E2E"},
        headers=auth_headers,
    )
    assert export_response.status_code == 201
    export_data = export_response.json()
    report_id = export_data["report_id"]
    assert export_data["structure_valid"] is True
    assert export_data["validation_status"] in ("APROVADO", "APROVADO_COM_RESSALVAS")
    assert export_data["reconciliation"]["receita_bruta_total"] == round(
        analysis_response.json()["financial_kpis"]["receita_bruta_total"], 2
    )

    reports = client.get(f"/api/projects/{project_id}/powerbi/reports", headers=auth_headers)
    assert reports.status_code == 200
    assert any(item["id"] == report_id for item in reports.json()["reports"])

    download = client.get(export_response.json()["download_url"], headers=auth_headers)
    assert download.status_code == 200
    assert download.content.startswith(b"PK")

    audit = client.get(f"/api/projects/{project_id}/audit", headers=auth_headers)
    assert audit.status_code == 200
    actions = {item["action"] for item in audit.json()["logs"]}
    assert {
        "PROJECT_CREATED",
        "DATASET_INGESTION_COMPLETED",
        "QUALITY_PROFILING_COMPLETED",
        "FINANCIAL_ESG_ANALYSIS_COMPLETED",
        "PREDICTIVE_ANALYSIS_EXECUTED",
        "SCENARIO_SIMULATION_COMPLETED",
        "ANALYSIS_VALIDATED",
        "POWERBI_PBIP_GENERATED_SUCCESSFULLY",
    }.issubset(actions)
