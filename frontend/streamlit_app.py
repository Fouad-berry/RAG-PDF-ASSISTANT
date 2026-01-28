import streamlit as st
import requests
import os
from datetime import datetime

# Configuration de la page
st.set_page_config(
    page_title="RAG PDF Assistant",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# URL de l'API backend - utilise l'URL Railway en production
API_BASE = os.getenv("BACKEND_URL", "http://localhost:8000")

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
    }
    .error-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
        color: #721c24;
    }
</style>
""", unsafe_allow_html=True)

# En-tête principal
st.markdown('<h1 class="main-header">📄 RAG PDF Assistant</h1>', unsafe_allow_html=True)
st.markdown("**Uploadez un PDF et posez des questions sur son contenu avec l'IA !**")

# Sidebar - Status et informations
st.sidebar.header("⚙️ Status du Système")

# Test de connexion à l'API
api_connected = False
try:
    response = requests.get(f"{API_BASE}/health", timeout=5)
    if response.status_code == 200:
        health_data = response.json()
        st.sidebar.success("✅ API Backend connectée")
        api_connected = True
        
        # Indicateur du modèle actuel
        model_type = health_data.get("model_type", "inconnu").lower()
        model_info = health_data.get("model_info", {})
        
        if model_type == "ollama":
            st.sidebar.success("🤖 **Mode OLLAMA** (Local)")
            st.sidebar.info(f"📋 Modèle: {model_info.get('llm_model', 'N/A')}")
            st.sidebar.info(f"🔤 Embedding: {model_info.get('embedding_model', 'N/A')}")
        elif model_type == "gemini":
            st.sidebar.success("🔥 **Mode GEMINI** (Cloud)")
            st.sidebar.info(f"📋 Modèle: {model_info.get('llm_model', 'N/A')}")
            st.sidebar.info(f"🔤 Embedding: {model_info.get('embedding_model', 'N/A')}")
        else:
            st.sidebar.warning(f"⚠️ Modèle: {model_type}")
        
except Exception as e:
    pass  # N'afficher l'erreur que si l'API n'est pas connectée

# Affichage du statut de connexion
if not api_connected:
    st.sidebar.error("❌ API Backend inaccessible")

# Message d'erreur si l'API n'est pas accessible
if not api_connected:
    st.error("🔧 **Backend non disponible**")
    st.warning("Veuillez démarrer le backend avec la commande: `cd backend && python -m uvicorn main:app --reload`")
    st.info("Rafraîchissez la page une fois le backend démarré.")
    st.markdown("---")

# Instructions dans la sidebar
st.sidebar.header("📋 Instructions")
st.sidebar.markdown("""
1. **Uploadez un PDF** (max 10MB)
2. **Cliquez sur "Indexer"** pour traiter le document
3. **Posez vos questions** dans la zone de texte
4. **Obtenez des réponses** basées sur le contenu du PDF

**Note :** Le traitement peut prendre quelques secondes selon la taille du document.
""")

# Interface principale - seulement si l'API est connectée
if api_connected:
    # Layout principal avec colonnes
    col1, col2 = st.columns([1, 1])

with col1:
    st.header("📤 Upload & Indexation PDF")
    
    uploaded_file = st.file_uploader(
        "Choisissez un fichier PDF",
        type="pdf",
        help="Maximum 10MB",
        key="pdf_uploader"
    )
    
    if uploaded_file is not None:
        # Afficher les infos du fichier
        file_size_mb = len(uploaded_file.getvalue()) / (1024 * 1024)
        st.info(f"📁 **Fichier:** {uploaded_file.name}")
        st.info(f"📊 **Taille:** {file_size_mb:.2f} MB")
        
        if st.button("🔄 Indexer le PDF", type="primary", use_container_width=True):
            if file_size_mb > 10:
                st.error("❌ Fichier trop volumineux (max 10MB)")
            else:
                with st.spinner("🔄 Indexation en cours..."):
                    # Préparer le fichier pour l'upload
                    files = {"file": (uploaded_file.name, uploaded_file.getvalue(), "application/pdf")}
                    
                    try:
                        response = requests.post(f"{API_BASE}/upload", files=files, timeout=180)  # Timeout étendu pour traitement
                        
                        if response.status_code == 200:
                            result = response.json()
                            st.success("✅ PDF indexé avec succès!")
                            
                            # Afficher les métriques
                            metrics_col1, metrics_col2 = st.columns(2)
                            with metrics_col1:
                                st.metric("📄 Chunks créés", result['chunks'])
                            with metrics_col2:
                                st.metric("🔤 Caractères", f"{result['total_chars']:,}")
                                
                            st.session_state.pdf_indexed = True
                            st.rerun()
                        else:
                            error_detail = response.json().get("detail", "Erreur inconnue")
                            st.error(f"❌ Erreur lors de l'indexation: {error_detail}")
                    except requests.exceptions.Timeout:
                        st.error("❌ Timeout: Le traitement prend plus de temps. Patientez et réessayez...")
                    except Exception as e:
                        st.error(f"❌ Erreur de connexion: {str(e)}")

with col2:
    st.header("❓ Questions & Réponses")
    
    # Zone de question
    question = st.text_area(
        "Posez votre question sur le PDF:",
        placeholder="Exemple: De quoi parle ce document ? Quels sont les points clés ?",
        height=100,
        key="question_input"
    )
    
    col_ask, col_clear = st.columns([3, 1])
    
    with col_ask:
        ask_button = st.button("🚀 Poser la question", type="primary", use_container_width=True, disabled=not question.strip())
    
    with col_clear:
        if st.button("🗑️ Effacer", use_container_width=True):
            st.session_state.question_input = ""
            if 'last_answer' in st.session_state:
                del st.session_state.last_answer
            st.rerun()
    
    if ask_button and question.strip():
        with st.spinner("🧠 Traitement de votre question..."):
            try:
                # Afficher un indicateur de progression
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                status_text.text("🔍 Recherche des passages pertinents...")
                progress_bar.progress(25)
                
                response = requests.post(
                    f"{API_BASE}/ask",
                    json={"question": question.strip()},
                    timeout=120  # Timeout étendu pour traitement
                )
                
                progress_bar.progress(100)
                status_text.text("✅ Réponse générée !")
                
                if response.status_code == 200:
                    result = response.json()
                    st.session_state.last_answer = result
                    # Nettoyer les indicateurs de progression
                    progress_bar.empty()
                    status_text.empty()
                    st.rerun()
                else:
                    # Nettoyer les indicateurs en cas d'erreur
                    progress_bar.empty()
                    status_text.empty()
                    error_detail = response.json().get("detail", "Erreur inconnue")
                    st.error(f"❌ Erreur: {error_detail}")
            except requests.exceptions.Timeout:
                st.error("❌ Timeout: Le traitement prend plus de temps. Patientez et réessayez...")
            except Exception as e:
                st.error(f"❌ Erreur de connexion: {str(e)}")

# Affichage de la dernière réponse
if 'last_answer' in st.session_state:
    st.header("🤖 Dernière Réponse")
    result = st.session_state.last_answer
    
    # Réponse principale
    st.markdown("### 💬 Réponse:")
    st.write(result["answer"])
    
    # Sources
    if result.get("sources"):
        st.markdown("### 📚 Sources utilisées:")
        
        for i, source in enumerate(result["sources"]):
            with st.expander(f"📄 Source {i+1} - {source['source']} (Chunk {source['chunk_index']})"):
                st.text(source["content"])
                if source.get("upload_date"):
                    st.caption(f"📅 Uploadé: {source['upload_date'][:19].replace('T', ' ')}")

# Section fichiers uploadés
st.header("📂 Fichiers Uploadés")

try:
    response = requests.get(f"{API_BASE}/files")
    if response.status_code == 200:
        files_data = response.json()
        files = files_data.get("files", [])
        
        if files:
            st.success(f"📊 {len(files)} fichier(s) trouvé(s)")
            
            # Tableau des fichiers
            for file in files:
                col1, col2, col3, col4 = st.columns([3, 1, 2, 1])
                
                with col1:
                    st.write(f"📄 **{file['filename']}**")
                with col2:
                    st.write(f"📊 {file['size_mb']} MB")
                with col3:
                    upload_date = datetime.fromisoformat(file['upload_date']).strftime("%d/%m/%Y %H:%M")
                    st.write(f"📅 {upload_date}")
                with col4:
                    if st.button("🗑️", key=f"delete_{file['filename']}", help="Supprimer ce fichier"):
                        # Confirmation de suppression
                        if f"confirm_delete_{file['filename']}" not in st.session_state:
                            st.session_state[f"confirm_delete_{file['filename']}"] = True
                            st.rerun()
                
                # Gestion de la confirmation
                if st.session_state.get(f"confirm_delete_{file['filename']}", False):
                    st.warning(f"⚠️ Confirmer la suppression de **{file['filename']}** ?")
                    col_yes, col_no = st.columns([1, 1])
                    
                    with col_yes:
                        if st.button("✅ Confirmer", key=f"confirm_yes_{file['filename']}"):
                            try:
                                with st.spinner("🗑️ Suppression en cours..."):
                                    response = requests.delete(f"{API_BASE}/files/{file['filename']}")
                                    
                                if response.status_code == 200:
                                    st.success(f"✅ {file['filename']} supprimé avec succès!")
                                    # Nettoyer la session et rafraîchir
                                    del st.session_state[f"confirm_delete_{file['filename']}"]
                                    st.rerun()
                                else:
                                    error_detail = response.json().get("detail", "Erreur inconnue")
                                    st.error(f"❌ Erreur: {error_detail}")
                            except Exception as e:
                                st.error(f"❌ Erreur de connexion: {str(e)}")
                    
                    with col_no:
                        if st.button("❌ Annuler", key=f"confirm_no_{file['filename']}"):
                            del st.session_state[f"confirm_delete_{file['filename']}"]
                            st.rerun()
        else:
            st.info("📁 Aucun fichier uploadé pour le moment.")
    else:
        st.warning("⚠️ Impossible de récupérer la liste des fichiers.")
except Exception as e:
    st.error(f"❌ Erreur lors de la récupération des fichiers: {str(e)}")

# Fin de l'interface principale (si API connectée)

# Footer
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: #666; padding: 1rem;'>"
    "RAG PDF Assistant - Powered by FastAPI, LangChain & Streamlit"
    "</div>", 
    unsafe_allow_html=True
)