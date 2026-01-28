#!/usr/bin/env python3
"""Script pour lister les modèles Gemini disponibles"""

import os
from dotenv import load_dotenv
from pathlib import Path

# Charger les variables d'environnement
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

try:
    import google.generativeai as genai
    
    # Configurer l'API avec la clé
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    if not GOOGLE_API_KEY:
        print("❌ GOOGLE_API_KEY non trouvée dans .env")
        exit(1)
    
    genai.configure(api_key=GOOGLE_API_KEY)
    
    print("🔍 Listing des modèles Gemini disponibles...")
    print("=" * 60)
    
    # Lister tous les modèles
    models = genai.list_models()
    
    embedding_models = []
    text_models = []
    other_models = []
    
    for model in models:
        model_name = model.name
        supported_methods = [method for method in model.supported_generation_methods]
        
        print(f"📋 Modèle: {model_name}")
        print(f"   Méthodes supportées: {supported_methods}")
        
        if 'embedContent' in supported_methods:
            embedding_models.append(model_name)
        elif 'generateContent' in supported_methods:
            text_models.append(model_name)
        else:
            other_models.append(model_name)
        print()
    
    print("=" * 60)
    print("📊 RÉSUMÉ:")
    print(f"🔤 Modèles d'embedding ({len(embedding_models)}):")
    for model in embedding_models:
        print(f"   ✅ {model}")
    
    print(f"\n💬 Modèles de texte ({len(text_models)}):")
    for model in text_models[:5]:  # Limiter l'affichage
        print(f"   ✅ {model}")
    if len(text_models) > 5:
        print(f"   ... et {len(text_models) - 5} autres")
    
    if other_models:
        print(f"\n❓ Autres modèles ({len(other_models)}):")
        for model in other_models:
            print(f"   ⚙️ {model}")
    
    print("\n🎯 Pour utiliser un modèle d'embedding, utilisez le nom exact ci-dessus.")
    
except ImportError:
    print("❌ Module google.generativeai non installé")
    print("Installez avec: pip install google-generativeai")
except Exception as e:
    print(f"❌ Erreur: {e}")