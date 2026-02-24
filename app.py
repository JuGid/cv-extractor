import streamlit as st
import fitz  # PyMuPDF
import re
import requests
import json

# Configuration de la page
st.set_page_config(page_title="PDF to HubSpot", layout="centered")
st.title("📄 Extracteur de CV vers HubSpot")

# Configuration HubSpot (Idéalement via Streamlit Secrets)
HUBSPOT_TOKEN = st.sidebar.text_input("HubSpot Access Token", type="password")

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
            "hs_lead_status": "0. Lead"
        }
    }
    response = requests.post(url, headers=headers, data=json.dumps(data))
    return response

# Interface d'upload
uploaded_files = st.file_uploader("Choisissez des CV (PDF)", type="pdf", accept_multiple_files=True)

if uploaded_files:
    if not HUBSPOT_TOKEN:
        st.warning("Veuillez entrer votre token HubSpot dans la barre latérale.")
    else:
        for uploaded_file in uploaded_files:
            # Lecture du PDF
            with fitz.open(stream=uploaded_file.read(), filetype="pdf") as doc:
                text = ""
                for page in doc:
                    text += page.get_text()
            
            email, fname, lname = extract_info(text)
            
            st.write(f"---")
            st.write(f"**Fichier :** {uploaded_file.name}")
            st.write(f"**Trouvé :** {fname} {lname} ({email})")
            
            if email:
                if st.button(f"Envoyer {fname} vers HubSpot", key=email):
                    res = send_to_hubspot(email, fname, lname)
                    if res.status_code in [201, 200]:
                        st.success("Contact ajouté !")
                    else:
                        st.error(f"Erreur HubSpot : {res.json().get('message')}")
            else:
                st.error("Impossible d'extraire l'email pour ce contact.")
