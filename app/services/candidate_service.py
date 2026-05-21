from app.repositories.store import RepositoryStore
from app.schemas.candidates import (
    CandidateCreate,
    CandidateDocument,
    EmployeeCreate,
    EmployeeDocument,
    NormalizedIdentity,
    ResumeUploadMockRequest,
)
from app.services.ai_extraction import AIExtractionProvider, MockAIExtractionProvider
from app.services.resume_parser import MockResumeParser, ResumeParser


class CandidateService:
    def __init__(self, store: RepositoryStore) -> None:
        self.store = store
        self.resume_parser: ResumeParser = MockResumeParser()
        self.ai_extractor: AIExtractionProvider = MockAIExtractionProvider()

    async def create_candidate(self, request: CandidateCreate) -> CandidateDocument:
        return await self.store.candidates.create(
            CandidateDocument(identity=request.identity, source=request.source)
        )

    async def mock_resume_upload(self, request: ResumeUploadMockRequest) -> CandidateDocument:
        parsed_resume = await self.resume_parser.parse(request.file_name)
        identity = await self.ai_extractor.extract_entities(
            parsed_resume,
            hints={
                "full_name": request.extracted_full_name,
                "email": request.email,
                "phone": request.phone,
            },
        )
        return await self.store.candidates.create(
            CandidateDocument(
                identity=identity,
                source="mock_resume_upload",
                metadata={
                    "file_name": request.file_name,
                    "resume_retained": False,
                    "parser": parsed_resume.metadata,
                    "ai_extraction_provider": "mock",
                },
            )
        )

    async def list_candidates(self) -> list[CandidateDocument]:
        return await self.store.candidates.list()

    async def get_candidate(self, candidate_id: str) -> CandidateDocument | None:
        return await self.store.candidates.get(candidate_id)

    async def create_employee(self, request: EmployeeCreate) -> EmployeeDocument:
        return await self.store.employees.create(
            EmployeeDocument(
                identity=request.identity,
                candidate_id=request.candidate_id,
                department=request.department,
                role=request.role,
            )
        )

    async def promote_candidate(
        self,
        candidate_id: str,
        department: str | None = None,
        role: str | None = None,
    ) -> EmployeeDocument | None:
        candidate = await self.store.candidates.get(candidate_id)
        if not candidate:
            return None
        employee = await self.store.employees.create(
            EmployeeDocument(
                identity=candidate.identity,
                candidate_id=candidate.id,
                department=department,
                role=role,
                metadata={"promoted_from_candidate": True},
            )
        )
        await self.store.candidates.update(candidate.id, {"promoted_employee_id": employee.id})
        return employee

    async def list_employees(self) -> list[EmployeeDocument]:
        return await self.store.employees.list()

    async def get_employee(self, employee_id: str) -> EmployeeDocument | None:
        return await self.store.employees.get(employee_id)

    async def seed_demo_data(self) -> list[CandidateDocument]:
        from app.data.seed import SEED_CANDIDATES

        existing = await self.store.candidates.list()
        existing_cases = {
            candidate.metadata.get("dataset_case")
            for candidate in existing
            if candidate.metadata.get("dataset_case")
        }
        for candidate in SEED_CANDIDATES:
            dataset_case = candidate.metadata.get("dataset_case")
            if dataset_case not in existing_cases:
                await self.store.candidates.create(candidate)
        return await self.store.candidates.list()
