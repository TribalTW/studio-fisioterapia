import streamlit as st
import pandas as pd
import hashlib
import secrets
from datetime import datetime
from sqlalchemy import text

# Configurazione della pagina
st.set_page_config(
    page_title="Gestionale Studio Postura & Pilates",
    page_icon="🧘‍♀️",
    layout="wide"
)

# ---------------------------------------------------------
# 1. CONNESSIONE AL DATABASE CLOUD (SUPABASE / POSTGRESQL)
# ---------------------------------------------------------
try:
    conn = st.connection("postgresql", type="sql")
except Exception as e:
    st.error(f"Errore di connessione al database cloud: {e}")
    st.stop()

# ---------------------------------------------------------
# 2. INIZIALIZZAZIONE TABELLE NEL DATABASE
# ---------------------------------------------------------
def init_db():
    with conn.session as session:
        session.execute(text("""
            CREATE TABLE IF NOT EXISTS utenti (
                id SERIAL PRIMARY KEY,
                nome VARCHAR(100),
                cognome VARCHAR(100),
                email VARCHAR(255) UNIQUE,
                password TEXT,
                codice_fiscale VARCHAR(16),
                telefono VARCHAR(50)
            );
        """))
        session.execute(text("""
            CREATE TABLE IF NOT EXISTS prenotazioni (
                id SERIAL PRIMARY KEY,
                email VARCHAR(255),
                data VARCHAR(50),
                ora VARCHAR(50),
                tipo VARCHAR(50)
            );
        """))
        session.execute(text("""
            CREATE TABLE IF NOT EXISTS banned_devices (
                id SERIAL PRIMARY KEY,
                device_id VARCHAR(255) UNIQUE
            );
        """))
        session.execute(text("""
            CREATE TABLE IF NOT EXISTS orari_bloccati (
                id SERIAL PRIMARY KEY,
                data VARCHAR(50),
                fascia VARCHAR(100)
            );
        """))
        session.execute(text("""
            CREATE TABLE IF NOT EXISTS codici_seduta (
                id SERIAL PRIMARY KEY,
                codice VARCHAR(100),
                data VARCHAR(50)
            );
        """))
        session.commit()

init_db()

# ---------------------------------------------------------
# 3. CONFIGURAZIONE SICUREZZA (ADMIN PASSWORD DA SECRETS)
# ---------------------------------------------------------
ADMIN_PASSWORD = st.secrets.get("admin_password", "MiaPasswordFallback2026!")

# Funzioni di utilità per hashing password
def make_hash(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hash(password, hashed_text):
    if make_hash(password) == hashed_text:
        return True
    return False

# ---------------------------------------------------------
# 4. INTERFACCIA UTENTE PRINCIPALE
# ---------------------------------------------------------
st.title("🧘‍♀️ Studio Postura & Pilates - Gestionale")

menu = ["Home / Login", "Registrazione", "Area Utente", "Pannello Admin"]
scelta = st.sidebar.selectbox("Navigazione", menu)

# --- HOME / LOGIN ---
if scelta == "Home / Login":
    st.subheader("Accedi al tuo account")
    
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    
    if st.button("Login"):
        if email and password:
            df_utenti = conn.query("SELECT * FROM utenti WHERE email = :email;", params={"email": email}, ttl=0)
            if not df_utenti.empty:
                stored_pass = df_utenti.iloc[0]["password"]
                if check_hash(password, stored_pass):
                    st.session_state["logged_in"] = True
                    st.session_state["user_email"] = email
                    st.session_state["user_nome"] = df_utenti.iloc[0]["nome"]
                    st.success(f"Benvenuto/a {st.session_state['user_nome']}!")
                    st.rerun()
                else:
                    st.error("Password errata.")
            else:
                st.error("Email non registrata.")
        else:
            st.warning("Inserisci tutti i campi.")

# --- REGISTRAZIONE ---
elif scelta == "Registrazione":
    st.subheader("Registrati come nuovo cliente")
    
    nome = st.text_input("Nome")
    cognome = st.text_input("Cognome")
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    codice_fiscale = st.text_input("Codice Fiscale", max_chars=16).upper()
    telefono = st.text_input("Telefono")
    
    if st.button("Registrati"):
        if nome and cognome and email and password and codice_fiscale:
            try:
                hashed_pw = make_hash(password)
                with conn.session as session:
                    session.execute(text("""
                        INSERT INTO utenti (nome, cognome, email, password, codice_fiscale, telefono)
                        VALUES (:nome, :cognome, :email, :password, :cf, :telefono);
                    """), {
                        "nome": nome, "cognome": cognome, "email": email,
                        "password": hashed_pw, "cf": codice_fiscale, "telefono": telefono
                    })
                    session.commit()
                st.success("Registrazione completata con successo! Ora puoi effettuare il login.")
            except Exception as e:
                st.error(f"Errore durante la registrazione (potrebbe esserci già un account con questa email): {e}")
        else:
            st.warning("Compompila tutti i campi obbligatori.")

# --- AREA UTENTE ---
elif scelta == "Area Utente":
    if "logged_in" not in st.session_state or not st.session_state["logged_in"]:
        st.warning("Effettua prima il login per accedere a questa sezione.")
    else:
        st.subheader(f"Benvenuto/a nell'Area Riservata, {st.session_state['user_nome']}")
        
        tab1, tab2 = st.tabs(["📅 Prenotazioni", "📱 Check-in & Info"])
        
        with tab1:
            st.write("### Prenota la tua seduta")
            data_seduta = st.date_input("Seleziona la data")
            ora_seduta = st.selectbox("Seleziona l'orario", ["09:00", "10:30", "15:00", "16:30", "18:00"])
            tipo_seduta = st.selectbox("Tipo di seduta", ["Individuale", "Duetto"])
            
            if st.button("Conferma Prenotazione"):
                with conn.session as session:
                    session.execute(text("""
                        INSERT INTO prenotazioni (email, data, ora, tipo)
                        VALUES (:email, :data, :ora, :tipo);
                    """), {
                        "email": st.session_state["user_email"],
                        "data": str(data_seduta),
                        "ora": ora_seduta,
                        "tipo": tipo_seduta
                    })
                    session.commit()
                st.success("Prenotazione registrata con successo nel cloud!")
            
            st.write("---")
            st.write("### Le tue prenotazioni attive:")
            df_prenotazioni = conn.query(
                "SELECT * FROM prenotazioni WHERE email = :email;",
                params={"email": st.session_state["user_email"]},
                ttl=0
            )
            if not df_prenotazioni.empty:
                st.dataframe(df_prenotazioni, use_container_width=True)
            else:
                st.info("Non hai ancora prenotazioni attive.")

        with tab2:
            st.write("### Check-in in Studio & Calendario")
            st.info("Inquadra il QR code in studio per convalidare la tua presenza oppure scarica il promemoria per il calendario.")

# --- PANNELLO ADMIN ---
elif scelta == "Pannello Admin":
    st.subheader("🔐 Accesso Pannello Amministratore")
    admin_pass_input = st.text_input("Password Admin", type="password")
    
    if st.button("Entra come Admin"):
        if admin_pass_input == ADMIN_PASSWORD:
            st.session_state["admin_logged"] = True
        else:
            st.error("Password amministratore non valida.")
            
    if st.session_state.get("admin_logged", False):
        st.success("Accesso amministratore effettuato!")
        
        admin_tab1, admin_tab2, admin_tab3 = st.tabs(["👥 Gestione Utenti & Prenotazioni", "📊 Statistiche", "⚙️ Gestione Orari"])
        
        with admin_tab1:
            st.write("### Tutti gli utenti registrati")
            df_all_users = conn.query("SELECT id, nome, cognome, email, codice_fiscale, telefono FROM utenti;", ttl=0)
            st.dataframe(df_all_users, use_container_width=True)
            
            st.write("### Tutte le prenotazioni")
            df_all_prenotazioni = conn.query("SELECT * FROM prenotazioni;", ttl=0)
            st.dataframe(df_all_prenotazioni, use_container_width=True)
            
        with admin_tab2:
            st.write("### Panoramica Statistiche")
            total_users = len(df_all_users) if 'df_all_users' in locals() else 0
            total_prenotazioni = len(df_all_prenotazioni) if 'df_all_prenotazioni' in locals() else 0
            
            col1, col2 = st.columns(2)
            col1.metric("Utenti Registrati", total_users)
            col2.metric("Prenotazioni Totali", total_prenotazioni)
            
        with admin_tab3:
            st.write("### Gestione Blocchi Orari e Giornate")
            data_blocco = st.date_input("Seleziona data da bloccare")
            if st.button("Blocca intera giornata"):
                with conn.session as session:
                    session.execute(text("INSERT INTO orari_bloccati (data, fascia) VALUES (:data, :fascia);"),
                                    {"data": str(data_blocco), "fascia": "INTERA_GIORNATA"})
                    session.commit()
                st.success(f"La giornata {data_blocco} è stata bloccata con successo.")
