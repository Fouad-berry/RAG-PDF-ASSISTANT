import streamlit as st
import pypdf  # Remplace PyMuPDF
import os
import tempfile
import shutil
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path
from dotenv import load_dotenv
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain.schema import Document

# Imports conditionnels pour Gemini
try:
    from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

# Configuration de la page
st.set_page_config(
    page_title="RAG PDF Assistant",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Charger les variables d'environnement
load_dotenv()

# Configuration des modèles
@st.cache_resource
def get_ai_models():
    """Initialise les modèles AI selon l'environnement"""
    google_api_key = os.getenv("GOOGLE_API_KEY")
    
    # Utiliser Gemini si la clé API est disponible (dev ou prod)
    if google_api_key and GEMINI_AVAILABLE:
        try:
            embeddings = GoogleGenerativeAIEmbeddings(
                model="models/gemini-embedding-001", 
                google_api_key=google_api_key
            )
            llm = ChatGoogleGenerativeAI(
                model="models/gemini-2.5-flash", 
                google_api_key=google_api_key, 
                temperature=0.2
            )
            environment = os.getenv("ENVIRONMENT", "development")
            model_type = f"Gemini ({environment.title()})"
            return embeddings, llm, model_type
        except Exception as e:
            st.error(f"❌ Erreur configuration Gemini: {str(e)}")
            st.stop()
    else:
        # Messages d'erreur plus précis
        if not GEMINI_AVAILABLE:
            st.error("❌ langchain-google-genai non installé")
        elif not google_api_key:
            st.error("❌ GOOGLE_API_KEY manquante dans .env")
        else:
            st.error("❌ Configuration manquante pour les modèles AI")
        
        st.markdown("""
        ### 🔧 Pour corriger :
        1. **Vérifier .env** : `GOOGLE_API_KEY=ta_clé_ici`
        2. **Redémarrer** l'application
        3. **Clé Gemini** : [Google AI Studio](https://aistudio.google.com/app/apikey)
        """)
        st.stop()

# CSS personnalisé
st.markdown("""
<style>
    .main-header {
        text-align: center;
        color: #1f77b4;
        margin-bottom: 2rem;
    }
    .success-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
        margin: 1rem 0;
    }
    .info-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #d1ecf1;
        border: 1px solid #b8daff;
        color: #0c5460;
        margin: 1rem 0;
    }
    .error-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
        color: #721c24;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Fonctions utilitaires
def extract_text_from_pdf(uploaded_file) -> str:
    """Extrait le texte d'un PDF uploadé avec pypdf"""
    try:
        # Créer un fichier temporaire
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            tmp_file.write(uploaded_file.read())
            tmp_path = tmp_file.name
        
        # Extraire le texte avec pypdf
        text = ""
        with open(tmp_path, 'rb') as file:
            pdf_reader = pypdf.PdfReader(file)
            
            # Extraire le texte de chaque page
            for page_num, page in enumerate(pdf_reader.pages):
                page_text = page.extract_text()
                if page_text.strip():  # Ignorer les pages vides
                    text += f"\n--- Page {page_num + 1} ---\n"
                    text += page_text + "\n"
        
        # Nettoyer le fichier temporaire
        os.unlink(tmp_path)
        
        if not text.strip():
            raise ValueError("Le PDF semble vide ou illisible")
        
        return text.strip()
    except Exception as e:
        raise Exception(f"Erreur lors de l'extraction du PDF: {str(e)}")

def create_vectorstore(text: str, filename: str, embeddings) -> Dict:
    """Crée un vectorstore à partir du texte"""
    # Découper en chunks
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=600,
        chunk_overlap=300,
        length_function=len,
        separators=["\\n\\n", "\\n", ".", "!", "?", "-", ",", " ", ""]
    )
    
    chunks = text_splitter.split_text(text)
    
    # Créer des documents avec métadonnées
    documents = [
        Document(
            page_content=chunk,
            metadata={
                "source": filename,
                "chunk_index": i,
                "upload_date": datetime.now().isoformat(),
                "total_chunks": len(chunks)
            }
        )
        for i, chunk in enumerate(chunks)
    ]
    
    # Créer le vectorstore
    vectorstore = FAISS.from_documents(documents, embeddings)
    
    return {
        "vectorstore": vectorstore,
        "chunks": len(chunks),
        "total_chars": len(text),
        "filename": filename
    }

def ask_question_to_documents(question: str, vectorstore, llm) -> str:
    """Pose une question sur les documents indexés"""
    # Recherche de similarité
    docs = vectorstore.similarity_search(question, k=6)
    
    if len(docs) < 2:
        return "❌ Pas assez de contexte trouvé. Essayez de reformuler votre question."
    
    # Construire le contexte
    context_text = "\\n\\n".join([doc.page_content for doc in docs])
    
    # Prompt optimisé
    prompt = f"""Contexte: {context_text}

Question: {question}

Instructions:
- Réponds de manière précise et détaillée en te basant uniquement sur le contexte fourni
- Si l'information n'est pas dans le contexte, indique-le clairement
- Utilise un français clair et professionnel
- Structure ta réponse de manière lisible

Réponse:"""
    
    try:
        response = llm.invoke(prompt)
        return response.content if hasattr(response, 'content') else str(response)
    except Exception as e:
        return f"❌ Erreur lors de la génération de la réponse: {str(e)}"

# Interface principale
def main():
    # Initialiser les modèles
    embeddings, llm, model_type = get_ai_models()
    
    # En-tête
    st.markdown('<h1 class="main-header">🤖 RAG PDF Assistant</h1>', unsafe_allow_html=True)
    
    # Sidebar - Informations et statut
    with st.sidebar:
        st.markdown("### ℹ️ Informations")
        st.markdown(f"**Modèle:** {model_type}")
        
        # Informations d'utilisation
        st.markdown("---")
        st.markdown("### 📋 Comment utiliser")
        st.markdown("""
        1. **Uploadez** un document PDF
        2. **Attendez** l'indexation 
        3. **Posez** vos questions
        4. **Obtenez** des réponses précises
        """)
        
        st.markdown("---")
        st.markdown("### ⚡ Optimisations")
        st.markdown("""
        - ✅ Extraction de texte rapide
        - ✅ Recherche sémantique avancée
        - ✅ Réponses contextuelles
        - ✅ Interface intuitive
        """)
        
        if 'vectorstore' in st.session_state:
            st.markdown("---")
            st.markdown("### 📊 Document actuel")
            info = st.session_state.get('document_info', {})
            st.markdown(f"**Fichier:** {info.get('filename', 'N/A')}")
            st.markdown(f"**Chunks:** {info.get('chunks', 0)}")
            st.markdown(f"**Caractères:** {info.get('total_chars', 0):,}")
    
    # Zone principale
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown("### 📄 Upload de document")
        uploaded_file = st.file_uploader(
            "Choisissez un fichier PDF",
            type=['pdf'],
            help="Uploadez un document PDF pour l'analyser avec l'IA"
        )
        
        if uploaded_file is not None:
            with st.spinner("🔄 Traitement du document..."):
                try:
                    # Extraire le texte
                    text = extract_text_from_pdf(uploaded_file)
                    
                    # Créer le vectorstore
                    result = create_vectorstore(text, uploaded_file.name, embeddings)
                    
                    # Stocker dans la session
                    st.session_state.vectorstore = result["vectorstore"]
                    st.session_state.document_info = result
                    
                    # Affichage du succès
                    st.markdown(f"""
                    <div class="success-box">
                        <strong>✅ Document traité avec succès !</strong><br>
                        📄 <strong>Fichier:</strong> {result['filename']}<br>
                        🔢 <strong>Chunks créés:</strong> {result['chunks']}<br>
                        📝 <strong>Caractères totaux:</strong> {result['total_chars']:,}
                    </div>
                    """, unsafe_allow_html=True)
                    
                except Exception as e:
                    st.markdown(f"""
                    <div class="error-box">
                        <strong>❌ Erreur de traitement</strong><br>
                        {str(e)}
                    </div>
                    """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("### 🤔 Posez vos questions")
        
        if 'vectorstore' in st.session_state:
            # Zone de question
            user_question = st.text_area(
                "Votre question:",
                placeholder="Ex: Quelles sont les compétences principales mentionnées ?",
                help="Posez une question précise sur le contenu du document"
            )
            
            if st.button("🔍 Rechercher", type="primary"):
                if user_question.strip():
                    with st.spinner("🤖 Génération de la réponse..."):
                        try:
                            response = ask_question_to_documents(
                                user_question, 
                                st.session_state.vectorstore, 
                                llm
                            )
                            
                            # Afficher la réponse
                            st.markdown("### 💬 Réponse")
                            st.markdown(f"""
                            <div class="info-box">
                                {response}
                            </div>
                            """, unsafe_allow_html=True)
                            
                        except Exception as e:
                            st.error(f"Erreur: {str(e)}")
                else:
                    st.warning("⚠️ Veuillez poser une question")
        else:
            st.markdown("""
            <div class="info-box">
                📄 <strong>Uploadez d'abord un document PDF</strong> pour commencer à poser des questions.
            </div>
            """, unsafe_allow_html=True)
    
    # Section historique des questions (optionnelle)
    if 'vectorstore' in st.session_state:
        st.markdown("---")
        st.markdown("### 💡 Questions suggérées")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("📋 Résumé général"):
                st.session_state.suggested_question = "Peux-tu faire un résumé général de ce document ?"
        
        with col2:
            if st.button("🎯 Points clés"):
                st.session_state.suggested_question = "Quels sont les points les plus importants ?"
        
        with col3:
            if st.button("🔍 Informations spécifiques"):
                st.session_state.suggested_question = "Quelles informations spécifiques sont mentionnées ?"

if __name__ == "__main__":
    main()