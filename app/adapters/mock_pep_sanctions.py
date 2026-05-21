from app.adapters.base import VendorAdapter
from app.schemas.common import RiskLevel, ScreeningType, utc_now
from app.schemas.payloads import PayloadEntryDocument
from app.schemas.screening import Finding, NormalizedScreeningResult


PEP_NAMES = {
    "boris johnson": "Former Prime Minister of the United Kingdom",
    "thaksin shinawatra": "Former Prime Minister of Thailand",
    "najib razak": "Former Prime Minister of Malaysia",
}

SANCTIONS_NAMES = {
    "oleg deripaska": "Mock OFAC SDN sanctions list match",
}


class MockPepSanctionsAdapter(VendorAdapter):
    vendor_name = "mock_pep_sanctions"

    async def submit_payload(self, entries: list[PayloadEntryDocument]) -> str:
        return f"ps-demo-{len(entries)}"

    async def poll_results(self, execution_id: str, entries: list[PayloadEntryDocument]) -> dict:
        results = []
        for entry in entries:
            name = entry.identity.full_name.lower()
            pep = PEP_NAMES.get(name)
            sanctions = SANCTIONS_NAMES.get(name)
            score = 92 if sanctions else 78 if pep else 2
            results.append(
                {
                    "payload_entry_id": entry.id,
                    "entity_id": entry.entity_id,
                    "pep": pep,
                    "sanctions": sanctions,
                    "risk_score": score,
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
            if item["pep"]:
                findings.append(
                    Finding(
                        source="Mock PEP Watchlist",
                        title="PEP match",
                        matched_name=entry.identity.full_name,
                        match_score=0.96,
                        severity="medium",
                        details=item["pep"],
                    )
                )
            if item["sanctions"]:
                findings.append(
                    Finding(
                        source="Mock Sanctions Watchlist",
                        title="Sanctions match",
                        matched_name=entry.identity.full_name,
                        match_score=0.98,
                        severity="high",
                        details=item["sanctions"],
                    )
                )
            normalized.append(
                NormalizedScreeningResult(
                    run_id=run_id,
                    payload_entry_id=entry.id,
                    entity_id=entry.entity_id,
                    entity_type=entry.entity_type,
                    vendor=self.vendor_name,
                    screening_type=ScreeningType.PEP_SANCTIONS,
                    match_status="MATCH" if findings else "CLEAR",
                    risk_score=score,
                    risk_level=risk_level,
                    findings=findings,
                    completed_at=utc_now().isoformat(),
                )
            )
        return normalized
