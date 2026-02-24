import streamlit as st
import fitz  # PyMuPDF
import re
import requests
import json

# Configuration de la page
st.set_page_config(page_title="PDF to HubSpot", layout="centered")
st.title("📄 Extracteur de CV vers HubSpot")

HUBSPOT_TOKEN = st.secrets.get("HUBSPOT_TOKEN", None)

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
uploaded_files = st.file_uploader("Choisissez des CV (PDF) v0.0.5", type="pdf", accept_multiple_files=True)

if uploaded_files:
    if not HUBSPOT_TOKEN:
        st.warning("⚠️ Token manquant dans les secrets.")
    else:
        # Liste pour stocker les infos extraites afin de les traiter globalement
        extracted_data_list = []

        for i, uploaded_file in enumerate(uploaded_files):
            # Extraction (Note: pour optimiser, on pourrait mettre ceci en cache)
            with fitz.open(stream=uploaded_file.read(), filetype="pdf") as doc:
                text = "".join([page.get_text() for page in doc])
            
            email_ext, fn_ext, ln_ext = extract_info(text)
            
            with st.expander(f"📄 {uploaded_file.name}", expanded=True):
                col1, col2 = st.columns(2)
                # On stocke les widgets dans extracted_data_list pour y accéder plus tard
                with col1:
                    fn = st.text_input("Prénom", value=fn_ext, key=f"fn_{i}")
                    ln = st.text_input("Nom", value=ln_ext, key=f"ln_{i}")
                with col2:
                    em = st.text_input("Email", value=email_ext, key=f"em_{i}")
                
                # On prépare les données pour l'envoi groupé
                extracted_data_list.append({"email": em, "fname": fn, "lname": ln})

        st.divider()

        # --- BOUTON VALIDER TOUT ---
        if st.button("🚀 Valider tout et envoyer dans HubSpot", use_container_width=True, type="primary"):
            success_count = 0
            error_count = 0
            
            progress_bar = st.progress(0)
            
            for index, data in enumerate(extracted_data_list):
                if not data["email"]:
                    st.error(f"❌ Email manquant pour {data['fname']}. Ignoré.")
                    error_count += 1
                    continue
                
                res = send_to_hubspot(data["email"], data["fname"], data["lname"])
                
                if res.status_code in [200, 201]:
                    success_count += 1
                else:
                    st.error(f"Erreur pour {data['email']}: {res.json().get('message')}")
                    error_count += 1
                
                # Mise à jour de la barre de progression
                progress_bar.progress((index + 1) / len(extracted_data_list))

            st.success(f"Terminé ! {success_count} contacts ajoutés, {error_count} erreurs.")
