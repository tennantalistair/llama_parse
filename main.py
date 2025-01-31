from fastapi import FastAPI, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import uuid
from typing import Dict, Any
import os
from llama_parse import LlamaParse
from llama_parse.plugins import PDFPlumber

app = FastAPI(title="Document Parser API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Store job statuses and results
jobs: Dict[str, Dict[str, Any]] = {}

@app.post("/parse")
async def parse_file(file: UploadFile):
    try:
        # Generate unique job ID
        job_id = str(uuid.uuid4())
        
        # Store initial job status
        jobs[job_id] = {"status": "processing"}
        
        # Start processing in background
        asyncio.create_task(process_file(job_id, file))
        
        return {"id": job_id, "status": "processing"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/status/{job_id}")
async def get_status(job_id: str):
    if job_id not in jobs:
        return {"status": "not_found"}
    return jobs[job_id]

async def process_file(job_id: str, file: UploadFile):
    file_path = None
    try:
        # Save uploaded file temporarily
        file_path = f"/tmp/{file.filename}"
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)

        # Initialize parser with API key from environment
        api_key = os.getenv("LLAMA_CLOUD_API_KEY")
        if not api_key:
            raise Exception("LLAMA_CLOUD_API_KEY not found in environment")

        parser = LlamaParse(
            api_key=api_key,
            result_type="markdown"
        )

        # Parse the document
        result = await parser.aparse(file_path)

        # Store successful result
        jobs[job_id] = {
            "status": "completed",
            "data": result
        }

    except Exception as e:
        # Store error status
        jobs[job_id] = {
            "status": "error",
            "error": str(e)
        }
    finally:
        # Cleanup
        if file_path and os.path.exists(file_path):
            os.remove(file_path)

# Add a simple health check endpoint
@app.get("/")
async def root():
    return {"status": "healthy", "message": "Document Parser API is running"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
