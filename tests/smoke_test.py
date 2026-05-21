from pathlib import Path
import sys

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.main import app


def test_demo_flow():
    with TestClient(app) as client:
        health = client.get("/health")
        assert health.status_code == 200
        assert "x-request-id" in health.headers
        assert health.json()["request_id"]

        seeded = client.post("/seed")
        assert seeded.status_code == 200
        candidates = seeded.json()["candidates"]
        assert len(candidates) >= 5

        reset = client.post("/demo/reset")
        assert reset.status_code == 200
        candidates = reset.json()["candidates"]
        assert reset.json()["candidate_count"] >= 5

        candidate_ids = [candidate["id"] for candidate in candidates[:4]]
        run = client.post(
            "/screening/runs",
            json={"build_payload": True, "candidate_ids": candidate_ids, "chunk_size": 2},
        )
        assert run.status_code == 200
        run_id = run.json()["id"]
        assert run.json()["batch_id"]

        dashboard = client.get(f"/dashboard/runs/{run_id}")
        assert dashboard.status_code == 200
        body = dashboard.json()
        assert body["summary"]["total_results"] == len(candidate_ids) * 2
        assert body["summary"]["alerts_or_matches"] >= 1

        reviewed = client.post(
            f"/results/{body['results'][0]['id']}/review",
            json={"action": "accept", "reviewer": "smoke-test", "note": "verified"},
        )
        assert reviewed.status_code == 200
        assert reviewed.json()["metadata"]["review"]["action"] == "accept"

        audit_logs = client.get("/audit/logs")
        assert audit_logs.status_code == 200
        assert len(audit_logs.json()) >= 1

        schedule = client.post("/schedules", json={"name": "Monthly employee rescreen"})
        assert schedule.status_code == 200
        task = client.post(f"/schedules/{schedule.json()['id']}/trigger")
        assert task.status_code == 200
        assert task.json()["task"]["task_type"] == "scheduled_screening"
        task_id = task.json()["task"]["id"]

        executed = client.post(f"/tasks/{task_id}/execute")
        assert executed.status_code == 200
        assert executed.json()["status"] == "COMPLETED"

        vendor_executions = client.get("/vendors/executions")
        assert vendor_executions.status_code == 200
        first_execution = vendor_executions.json()[0]
        webhook = client.post(
            f"/webhooks/vendors/{first_execution['vendor']}",
            json={
                "event_type": "results_ready",
                "external_execution_id": first_execution["external_execution_id"],
            },
        )
        assert webhook.status_code == 200


if __name__ == "__main__":
    test_demo_flow()
    print("Smoke test passed")
