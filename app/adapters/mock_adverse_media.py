from app.adapters.base import VendorAdapter
from app.schemas.common import RiskLevel, ScreeningType, utc_now
from app.schemas.payloads import PayloadEntryDocument
from app.schemas.screening import Finding, NormalizedScreeningResult


ADVERSE_NAMES = {
    "elizabeth holmes": {
        "score": 91,
        "title": "Fraud conviction and adverse media coverage",
        "details": "Mock adverse media hit adapted for demo screening.",
    },
    "carlos ghosn": {
        "score": 86,
        "title": "Corporate misconduct investigation coverage",
        "details": "Mock ranked adverse media article.",
    },
}


class MockAdverseMediaAdapter(VendorAdapter):
    vendor_name = "mock_adverse_media"

    async def submit_payload(self, entries: list[PayloadEntryDocument]) -> str:
        return f"am-demo-{len(entries)}"

    async def poll_results(self, execution_id: str, entries: list[PayloadEntryDocument]) -> dict:
        results = []
        for entry in entries:
            name = entry.identity.full_name.lower()
            match = ADVERSE_NAMES.get(name)
            results.append(
                {
                    "payload_entry_id": entry.id,
                    "entity_id": entry.entity_id,
                    "match": bool(match),
                    "risk_score": match["score"] if match else 3,
                    "article": match,
                }
            )
        return {"execution_id": execution_id, "results": results}

    async def normalize_results(
        self,
        run_id: str,
        raw_response: dict,
        entries: list[PayloadEntryDocument],
    ) -> list[NormalizedScreeningResult]:
        entry_map = {entry.id: entry for entry in entries}
        normalized = []
        for item in raw_response["results"]:
            entry = entry_map[item["payload_entry_id"]]
            score = item["risk_score"]
            risk_level = RiskLevel.HIGH if score >= 71 else RiskLevel.MEDIUM if score >= 31 else RiskLevel.LOW
            findings = []
            if item["match"]:
                article = item["article"]
                findings.append(
                    Finding(
                        source="Mock News Index",
                        title=article["title"],
                        url="https://example.com/mock-adverse-media",
                        matched_name=entry.identity.full_name,
                        match_score=0.94,
                        severity="high",
                        details=article["details"],
                    )
                )
            normalized.append(
                NormalizedScreeningResult(
                    run_id=run_id,
                    payload_entry_id=entry.id,
                    entity_id=entry.entity_id,
                    entity_type=entry.entity_type,
                    vendor=self.vendor_name,
                    screening_type=ScreeningType.ADVERSE_MEDIA,
                    match_status="ALERT" if item["match"] else "CLEAR",
                    risk_score=score,
                    risk_level=risk_level,
                    findings=findings,
                    completed_at=utc_now().isoformat(),
                )
            )
        return normalized
