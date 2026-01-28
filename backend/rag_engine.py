import fitz  # PyMuPDF
import os
from datetime import datetime
from typing import Dict, List
from pathlib import Path
from dotenv import load_dotenv
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain.chains import RetrievalQA
from langchain.schema import Document
from langchain_community.llms import Ollama
from langchain_community.embeddings import OllamaEmbeddings

# Imports conditionnels pour Gemini
try:
    from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

# Charger les variables d'environnement en premier
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

# Configuration - Modèle utilisé (après chargement du .env)
USE_OLLAMA = os.getenv("USE_OLLAMA", "true").lower() == "true"  # Local (dev)
USE_GEMINI = os.getenv("USE_GEMINI", "false").lower() == "true"  # Déploiement (prod)

VECTORSTORE_PATH = "vectorstore"
DATA_PATH = "data"

# Configuration des modèles selon l'environnement
if USE_GEMINI and GEMINI_AVAILABLE:
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    if not GOOGLE_API_KEY:
        raise ValueError("GOOGLE_API_KEY requise pour Gemini. Ajoutez-la dans .env")
    
    embeddings = GoogleGenerativeAIEmbeddings(
        model="models/gemini-embedding-001", 
        google_api_key=GOOGLE_API_KEY
    )
    llm = ChatGoogleGenerativeAI(
        model="models/gemini-2.5-flash", 
        google_api_key=GOOGLE_API_KEY, 
        temperature=0.2
    )
    MODEL_TYPE = "gemini"
    
elif USE_OLLAMA:
    # Configuration Ollama (pour développement local)
    embeddings = OllamaEmbeddings(model="nomic-embed-text")
    llm = Ollama(model="llama3.2", temperature=0.2)
    MODEL_TYPE = "ollama"
    
else:
    raise ValueError("Aucun modèle configuré. Activez USE_OLLAMA ou USE_GEMINI dans .env")

# Variable globale pour le vectorstore
vectorstore = None

async def extract_text_from_pdf(file_path: str) -> str:
    """Extrait le texte d'un PDF avec PyMuPDF"""
    try:
        doc = fitz.open(file_path)
        text = ""
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            text += page.get_text()
            text += "\n"  # Saut de ligne entre les pages
        
        doc.close()
        
        if not text.strip():
            raise ValueError("Le PDF semble vide ou illisible")
        
        return text.strip()
    except Exception as e:
        raise Exception(f"Erreur lors de l'extraction du PDF: {str(e)}")

async def ingest_pdf(file_path: str, original_filename: str) -> Dict:
    """Ingère un PDF dans le vectorstore"""
    global vectorstore
    
    # Extraire le texte
    text = await extract_text_from_pdf(file_path)
    
    # Découper en chunks optimisés pour CV/documents professionnels
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=600,
        chunk_overlap=300,
        length_function=len,
        separators=["\n\n", "\n", ".", "!", "?", "-", ",", " ", ""]
    )
    
    chunks = text_splitter.split_text(text)
    
    # Créer des documents avec métadonnées
    documents = [
        Document(
            page_content=chunk,
            metadata={
                "source": original_filename,
                "chunk_index": i,
                "file_path": file_path,
                "upload_date": datetime.now().isoformat(),
                "total_chunks": len(chunks)
            }
        )
        for i, chunk in enumerate(chunks)
    ]
    
    # Créer le vectorstore
    vectorstore = FAISS.from_documents(documents, embeddings)
    
    # Sauvegarder localement
    os.makedirs(VECTORSTORE_PATH, exist_ok=True)
    vectorstore.save_local(VECTORSTORE_PATH)
    
    return {
        "chunks": len(chunks),
        "total_chars": len(text),
        "file_saved": file_path,
        "original_filename": original_filename
    }

async def ask_question(question: str) -> Dict:
    """Pose une question sur le contenu indexé"""
    global vectorstore
    
    if vectorstore is None:
        if os.path.exists(f"{VECTORSTORE_PATH}/index.faiss"):
            try:
                vectorstore = FAISS.load_local(VECTORSTORE_PATH, embeddings)
            except Exception as e:
                raise Exception(f"Impossible de charger le vectorstore: {str(e)}")
        else:
            raise Exception("Aucun document indexé. Veuillez d'abord uploader un PDF.")
    
    # Recherche et génération de réponse
    docs = vectorstore.similarity_search(question, k=8)
    
    if len(docs) < 3:
        raise Exception(f"Pas assez de contexte trouvé ({len(docs)} documents). Essayez de reformuler votre question.")
    
    context_text = "\n\n".join([doc.page_content for doc in docs[:6]])
    
    enhanced_prompt = f"""Contexte: {context_text}

Question: {question}

Instructions:
- Analysez le contexte pour répondre à la question
- Soyez précis et factuel
- Mentionnez les sources spécifiques si disponibles

Réponse:
"""
            
    response = llm.invoke(enhanced_prompt)
    answer = response.content if hasattr(response, 'content') else str(response)
            
    sources = []
    for i, doc in enumerate(docs[:5]):
        sources.append({
            "content": doc.page_content[:300] + "..." if len(doc.page_content) > 300 else doc.page_content,
            "source": doc.metadata.get("source", "Document"),
            "chunk_index": doc.metadata.get("chunk_index", i),
            "upload_date": doc.metadata.get("upload_date", "")
        })
    
    return {
        "answer": answer,
        "sources": sources,
        "context_used": len(sources)
    }

async def list_uploaded_files() -> List[Dict]:
    """Liste les fichiers PDF uploadés"""
    files = []
    
    if not os.path.exists(DATA_PATH):
        return files
    
    try:
        for filename in os.listdir(DATA_PATH):
            if filename.endswith('.pdf'):
                file_path = os.path.join(DATA_PATH, filename)
                stat = os.stat(file_path)
                
                files.append({
                    "filename": filename,
                    "size": stat.st_size,
                    "upload_date": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "size_mb": round(stat.st_size / (1024 * 1024), 2)
                })
        
        files.sort(key=lambda x: x["upload_date"], reverse=True)
        
    except Exception:
        pass
    
    return files

async def delete_pdf_file(filename: str) -> Dict:
    """Supprime un fichier PDF et reconstruit le vectorstore"""
    global vectorstore
    
    file_path = os.path.join(DATA_PATH, filename)
    
    if not os.path.exists(file_path):
        raise Exception(f"Fichier {filename} non trouvé")
    
    # Supprimer le fichier
    os.remove(file_path)
    
    # Réinitialiser le vectorstore
    vectorstore = None
    
    # Supprimer l'ancien vectorstore
    if os.path.exists(f"{VECTORSTORE_PATH}/index.faiss"):
        os.remove(f"{VECTORSTORE_PATH}/index.faiss")
    if os.path.exists(f"{VECTORSTORE_PATH}/index.pkl"):
        os.remove(f"{VECTORSTORE_PATH}/index.pkl")
    
    # Reconstruire le vectorstore avec les fichiers restants
    remaining_files = [f for f in os.listdir(DATA_PATH) if f.endswith('.pdf')]
    
    if remaining_files:
        # Recharger tous les fichiers restants
        all_documents = []
        
        for pdf_file in remaining_files:
            pdf_path = os.path.join(DATA_PATH, pdf_file)
            text = await extract_text_from_pdf(pdf_path)
            
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=600,
                chunk_overlap=300,
                length_function=len,
                separators=["\n\n", "\n", " ", ""]
            )
            
            chunks = text_splitter.split_text(text)
            
            documents = []
            for i, chunk in enumerate(chunks):
                doc = Document(
                    page_content=chunk,
                    metadata={
                        "source": pdf_file,
                        "chunk_index": i,
                        "upload_date": datetime.now().isoformat()
                    }
                )
                documents.append(doc)
            
            all_documents.extend(documents)
        
        if all_documents:
            vectorstore = FAISS.from_documents(all_documents, embeddings)
            vectorstore.save_local(VECTORSTORE_PATH)
    
    return {
        "message": f"Fichier {filename} supprimé avec succès",
        "remaining_files": len(remaining_files),
        "vectorstore_rebuilt": len(remaining_files) > 0
    }

# Configuration au démarrage
def init_directories():
    """Initialise les dossiers nécessaires"""
    os.makedirs(VECTORSTORE_PATH, exist_ok=True)
    os.makedirs(DATA_PATH, exist_ok=True)

if __name__ != "__main__":
    init_directories()