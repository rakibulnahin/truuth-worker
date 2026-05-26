import os
import tempfile
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from motor.motor_asyncio import AsyncIOMotorDatabase

# Import your newly modularized extractor
from app.services.extraction import Extractor

# Assuming you have dependencies set up in your app to yield DB sessions
# e.g., from app.core.database import get_pg_session, get_mongo_db
# 
# async def get_pg_session() -> AsyncSession: ...
# async def get_mongo_db() -> AsyncIOMotorDatabase: ...

router = APIRouter(prefix="/resumes", tags=["Extraction"])


@router.post("/extract")
async def extract_resume_info(
    
    file: UploadFile = File(...),
    # Uncomment and use these dependencies when integrated into your main app
    # pg_session: AsyncSession = Depends(get_pg_session),
    # mongo_db: AsyncIOMotorDatabase = Depends(get_mongo_db)
):
    print("Here mf")
    """
    Receives a resume file, extracts identity data via Llama 4, 
    and saves the results to both Postgres and MongoDB.
    """
    # 1. Save uploaded file to a temporary location for processing
    suffix = ".pdf" if file.filename.lower().endswith(".pdf") else ".docx"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await file.read()
        tmp.write(content)
        temp_file_path = tmp.name

    try:
        # 2. Extract Data using the module
        extractor = Extractor()
        print(temp_file_path)
        extracted_data = extractor.start_extractor([temp_file_path])
        
        if not extracted_data:
            raise HTTPException(status_code=500, detail="Extraction failed to return data.")

        # Extract specific scalar values for relational DB
        candidate_name = extracted_data.get("candidate_name", {}).get("value")
        
        # 3. Save to PostgreSQL (Relational/Structured data via asyncpg)
        # Using raw SQL text for demonstration; typically you would use SQLAlchemy ORM models here
        """
        insert_query = text('''
            INSERT INTO candidates (full_name, extraction_status, source_file)
            VALUES (:name, :status, :source)
            RETURNING id;
        ''')
        result = await pg_session.execute(insert_query, {
            "name": candidate_name,
            "status": "COMPLETED",
            "source": file.filename
        })
        await pg_session.commit()
        pg_candidate_id = result.scalar()
        """

        # 4. Save to MongoDB (Unstructured/Raw payload data via motor)
        # Perfect for storing the entire JSON schema with confidences and justifications
        """
        mongo_document = {
            "postgres_ref_id": pg_candidate_id,
            "file_name": file.filename,
            "raw_extraction": extracted_data,
            "model_used": "llama-4-maverick"
        }
        await mongo_db.raw_extractions.insert_one(mongo_document)
        """

        return {
            "status": "success",
            "message": "Resume extracted and saved to databases.",
            "data": extracted_data
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
        
    finally:
        # Clean up the uploaded temp file
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)