from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
from dotenv import load_dotenv
from rag_engine import ingest_pdf, ask_question, list_uploaded_files

# Charger le fichier .env depuis le répertoire parent
load_dotenv(dotenv_path="../.env")

app = FastAPI(title="RAG PDF Assistant API", version="1.0.0")

# CORS pour Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8501"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class QuestionRequest(BaseModel):
    question: str

@app.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    """Upload et indexe un fichier PDF"""
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Le fichier doit être un PDF")
    
    if file.size > 10 * 1024 * 1024:  # 10MB
        raise HTTPException(status_code=400, detail="Fichier trop volumineux (max 10MB)")
    
    # Lire le contenu du fichier
    content = await file.read()
    
    # Sauvegarder dans le dossier data
    os.makedirs("data", exist_ok=True)
    
    # Générer un nom de fichier sûr avec timestamp
    import datetime
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_filename = f"{timestamp}_{file.filename.replace(' ', '_')}"
    file_path = f"data/{safe_filename}"
    
    with open(file_path, "wb") as f:
        f.write(content)
    
    # Ingérer le PDF
    try:
        result = await ingest_pdf(file_path, file.filename)
        
        return {
            "success": True,
            "message": f"PDF '{file.filename}' indexé avec succès",
            "file_path": file_path,
            "chunks": result["chunks"],
            "total_chars": result["total_chars"]
        }
    except Exception as e:
        # Supprimer le fichier en cas d'erreur
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=500, detail=f"Erreur lors de l'ingestion: {str(e)}")

@app.post("/ask")
async def ask(request: QuestionRequest):
    """Pose une question sur le PDF indexé"""
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question vide")
    
    try:
        response = await ask_question(request.question)
        return {
            "question": request.question,
            "answer": response["answer"],
            "sources": response.get("sources", [])
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")

@app.get("/files")
async def get_files():
    """Récupère la liste des fichiers uploadés"""
    try:
        files = await list_uploaded_files()
        return {"files": files}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")

@app.get("/health")
async def health_check():
    """Check de santé de l'API"""
    from rag_engine import MODEL_TYPE
    
    # Informations détaillées sur le modèle actuel
    if MODEL_TYPE == "gemini":
        model_info = {
            "llm_model": "models/gemini-2.5-flash",
            "embedding_model": "models/gemini-embedding-001"
        }
    elif MODEL_TYPE == "ollama":
        model_info = {
            "llm_model": "llama3.2",
            "embedding_model": "nomic-embed-text"
        }
    else:
        model_info = {"status": "unknown"}
    
    return {
        "status": "healthy",
        "message": "RAG PDF Assistant API - Ready!",
        "model_type": MODEL_TYPE.upper(),
        "model_info": model_info,
        "gemini_configured": bool(os.getenv("GOOGLE_API_KEY")),
        "ollama_configured": bool(os.getenv("USE_OLLAMA", "false").lower() == "true")
    }

@app.delete("/files/{filename}")
async def delete_file(filename: str):
    """Supprime un fichier PDF et reconstruit le vectorstore"""
    try:
        from rag_engine import delete_pdf_file
        result = await delete_pdf_file(filename)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la suppression: {str(e)}")

@app.get("/")
async def root():
    return {"message": "RAG PDF Assistant API - Ready!", "docs": "/docs"}

if __name__ == "__main__":
    import uvicorn
    os.makedirs("../data", exist_ok=True)
    os.makedirs("../vectorstore", exist_ok=True)
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)