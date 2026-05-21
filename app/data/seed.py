from app.schemas.candidates import CandidateDocument, NormalizedIdentity


SEED_CANDIDATES = [
    CandidateDocument(
        identity=NormalizedIdentity(
            full_name="Sarah Thompson",
            first_name="Sarah",
            last_name="Thompson",
            date_of_birth="1992-07-14",
            nationality="Australian",
            identifiers={
                "email": "sarah.thompson92@gmail.com",
                "phone": "+61 412 345 678",
                "social_media": ["linkedin.com/in/sarah-thompson-92"],
            },
        ),
        metadata={"dataset_case": "C-001", "expected": "CLEAR"},
    ),
    CandidateDocument(
        identity=NormalizedIdentity(
            full_name="Boris Johnson",
            first_name="Boris",
            last_name="Johnson",
            date_of_birth="1964-06-19",
            nationality="British",
            identifiers={"email": "b.johnson64@mail.com", "phone": "+44 7700 900456"},
        ),
        metadata={"dataset_case": "P-001", "expected": "PEP MATCH"},
    ),
    CandidateDocument(
        identity=NormalizedIdentity(
            full_name="Thaksin Shinawatra",
            first_name="Thaksin",
            last_name="Shinawatra",
            date_of_birth="1949-07-26",
            nationality="Thai",
            identifiers={"email": "t.shinawatra@mail.com", "phone": "+66 81 234 5678"},
        ),
        metadata={"dataset_case": "P-002", "expected": "PEP MATCH"},
    ),
    CandidateDocument(
        identity=NormalizedIdentity(
            full_name="Oleg Deripaska",
            first_name="Oleg",
            last_name="Deripaska",
            date_of_birth="1968-01-02",
            nationality="Russian",
            identifiers={"email": "oleg.deripaska68@mail.com"},
        ),
        metadata={"dataset_case": "S-001", "expected": "SANCTIONS MATCH"},
    ),
    CandidateDocument(
        identity=NormalizedIdentity(
            full_name="Elizabeth Holmes",
            first_name="Elizabeth",
            last_name="Holmes",
            date_of_birth="1984-02-03",
            nationality="American",
            identifiers={"email": "e.holmes84@mail.com"},
        ),
        metadata={"dataset_case": "A-001", "expected": "ADVERSE MEDIA"},
    ),
    CandidateDocument(
        identity=NormalizedIdentity(
            full_name="Mei Chen",
            first_name="Mei",
            last_name="Chen",
            date_of_birth="1995-02-28",
            nationality="Singaporean",
            identifiers={"email": "mei.chen95@yahoo.com", "phone": "+65 9123 4567"},
        ),
        metadata={"dataset_case": "F-001", "expected": "FALSE POSITIVE CLEAR"},
    ),
]
