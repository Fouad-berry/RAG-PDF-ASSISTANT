# 🚀 Déploiement sur Render

## ✅ Prérequis

1. **Compte Render** : [render.com](https://render.com) (gratuit)
2. **Clé API Gemini** : [Google AI Studio](https://aistudio.google.com/app/apikey)
3. **Repo GitHub** : Votre code sur GitHub

## 🛠️ Configuration automatisée

Votre projet est prêt pour Render ! ✨

### Structure optimisée :
```
rag-psdf-assistant/
├── app.py                 # Application Streamlit tout-en-un
├── requirements.txt       # Dépendances Python simplifiées
├── Procfile              # Commande de démarrage
├── .streamlit/config.toml # Configuration Streamlit
└── .env.example          # Variables d'environnement
```

## 🚀 Déploiement en 3 étapes

### **1. Connecter GitHub à Render**
1. Va sur [render.com](https://render.com)
2. Clique "New +" → "Web Service"
3. Connecte ton repository `RAG-PDF-ASSISTANT`
4. Render détecte automatiquement Python

### **2. Configuration automatique**
Render va automatiquement :
- ✅ Détecter `requirements.txt`
- ✅ Utiliser `Procfile` pour le démarrage
- ✅ Installer les dépendances Python
- ✅ Configurer Streamlit

### **3. Variables d'environnement**
Dans les settings Render, ajoute :
```
GOOGLE_API_KEY=ta_clé_gemini_ici
ENVIRONMENT=production
```

## 🎯 Fonctionnalités incluses

✅ **Interface tout-en-un** : Upload + Questions dans Streamlit  
✅ **Extraction PDF** : PyMuPDF intégré  
✅ **Recherche sémantique** : FAISS vectorstore  
✅ **IA Gemini** : Réponses intelligentes  
✅ **Interface moderne** : CSS personnalisé  
✅ **Responsive** : Optimisé mobile/desktop  

## ⚡ Performance

- **RAM utilisée** : ~200 MB (< 512 MB limite gratuite)
- **Démarrage** : 30-60 secondes après réveil
- **Sleep** : 15 min d'inactivité → réveil automatique
- **Limite** : 750h/mois gratuit

## 🔧 Configuration avancée

### Variables d'environnement disponibles :
- `GOOGLE_API_KEY` : Clé API Gemini (requis)
- `ENVIRONMENT` : `production` ou `development`
- `DEBUG` : `true` ou `false`

### Optimisations incluses :
- Cache des modèles avec `@st.cache_resource`
- Gestion d'erreurs robuste
- Interface utilisateur intuitive
- Nettoyage automatique des fichiers temporaires

## 📊 Monitoring

### Render Dashboard :
- **Logs** : Temps réel dans l'interface
- **Métriques** : CPU, RAM, requêtes
- **Redéploiement** : Automatique à chaque push

### Health Check :
L'application démarre automatiquement et est accessible via l'URL générée.

## ⚠️ Limites du plan gratuit

- **Sleep automatique** : 15 min d'inactivité
- **Réveil** : 30-60 secondes
- **Stockage** : Fichiers temporaires (pas de persistance)
- **Vectorstore** : Recréé à chaque session

## 🆘 Dépannage

### **App ne démarre pas**
```bash
# Vérifier les logs Render
Error: ModuleNotFoundError
→ Vérifier requirements.txt
```

### **Erreur Gemini**
```bash
Error: Invalid API key
→ Vérifier GOOGLE_API_KEY dans settings
```

### **Sleep trop fréquent**
```bash
Solution: Plan payant $7/mois pour "always-on"
```

## 🎉 Prêt à déployer !

Ton assistant RAG PDF est optimisé pour Render. 
Après déploiement, tu auras une URL comme :
`https://ton-app.onrender.com`

🚀 **Let's go !**