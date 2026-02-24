import streamlit as st
import fitz  # PyMuPDF
import re
import requests
import json

# Configuration de la page
st.set_page_config(page_title="PDF to HubSpot", layout="centered")
st.title("📄 Extracteur de CV vers HubSpot")

# 1. Vérifier si le token est dans les Secrets Streamlit
secret_token = st.secrets.get("HUBSPOT_TOKEN", None)

# 2. Créer le champ dans la barre latérale avec le secret comme valeur par défaut
HUBSPOT_TOKEN = st.sidebar.text_input(
    "HubSpot Access Token", 
    value=secret_token if secret_token else "", 
    type="password",
)

def extract_info(text):
    """Extrait l'email et tente de trouver le nom/prénom"""
    # Regex pour l'email
    email_match = re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text)
    email = email_match.group(0) if email_match else None
    
    # Logique simplifiée pour le nom : on prend souvent les premières lignes
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    firstname, lastname = "Inconnu", "Inconnu"
    
    if len(lines) > 0:
        full_name = lines[0].split()
        if len(full_name) >= 2:
            firstname, lastname = full_name[0], " ".join(full_name[1:])
            
    return email, firstname, lastname

def send_to_hubspot(email, firstname, lastname):
    """Envoie les données vers l'API HubSpot"""
    url = "https://api.hubapi.com/crm/v3/objects/contacts"
    headers = {
        'Authorization': f'Bearer {HUBSPOT_TOKEN}',
        'Content-Type': 'application/json'
    }
    data = {
        "properties": {
            "email": email,
            "firstname": firstname,
            "lastname": lastname,
            "hs_lead_status": "0. Lead",
            "evenement_declenche": "Candidature Indeed"
        }
    }
    response = requests.post(url, headers=headers, data=json.dumps(data))
    return response

# Interface d'upload
uploaded_files = st.file_uploader("Choisissez des CV (PDF) v0.0.3", type="pdf", accept_multiple_files=True)

if uploaded_files:
    if not HUBSPOT_TOKEN:
        st.warning("⚠️ Veuillez configurer votre token HubSpot.")
    else:
        st.info(f"📂 {len(uploaded_files)} fichier(s) chargé(s). Vérifiez les informations ci-dessous :")
        
        for i, uploaded_file in enumerate(uploaded_files):
            # 1. Extraction du texte
            with fitz.open(stream=uploaded_file.read(), filetype="pdf") as doc:
                text = "".join([page.get_text() for page in doc])
            
            email_ext, fname_ext, lname_ext = extract_info(text)
            
            # 2. Création d'un formulaire d'édition pour chaque CV
            with st.expander(f"📄 Modifier : {uploaded_file.name}", expanded=True):
                col1, col2 = st.columns(2)
                
                with col1:
                    new_fname = st.text_input("Prénom", value=fname_ext, key=f"fn_{i}")
                    new_lname = st.text_input("Nom", value=lname_ext, key=f"ln_{i}")
                
                with col2:
                    new_email = st.text_input("Email", value=email_ext if email_ext else "", key=f"em_{i}")
                    # On peut même ajouter un sélecteur pour le statut si besoin
                    status = st.selectbox("Statut", ["0. Lead", "1. Contacté", "2. Entretien"], key=f"st_{i}")

                # 3. Bouton d'envoi avec les données MODIFIÉES
                if st.button(f"Valider et envoyer sur HubSpot", key=f"btn_{i}"):
                    if not new_email:
                        st.error("L'email est obligatoire pour créer un contact.")
                    else:
                        with st.spinner("Envoi en cours..."):
                            res = send_to_hubspot(new_email, new_fname, new_lname)
                            
                            if res.status_code in [201, 200]:
                                st.success(f"✅ {new_fname} a été ajouté avec succès !")
                            elif res.status_code == 409:
                                st.warning("⚠️ Ce contact existe déjà dans HubSpot.")
                            else:
                                st.error(f"Erreur {res.status_code}: {res.json().get('message')}")
