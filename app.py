from datetime import datetime, time, timedelta
import hashlib
import os
import re
import secrets
import uuid
from zoneinfo import ZoneInfo
import pandas as pd
import psycopg2
import streamlit as st
import streamlit.components.v1 as components
from sqlalchemy import create_engine, text

# Configurazione Pagina
st.set_page_config(
    page_title="Lola's Glam House",
    page_icon="💅",
    layout="centered",
)

# Connessione a Supabase / PostgreSQL con caching delle risorse
@st.cache_resource
def get_db_engine():
    db_url = st.secrets["supabase"]["db_url"]
    return create_engine(db_url, pool_pre_ping=True)

engine = get_db_engine()

# Inizializzazione Database PostgreSQL / Supabase (Eseguita una sola volta)
@st.cache_resource
def init_db():
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS prenotazioni (
                id SERIAL PRIMARY KEY,
                nome TEXT NOT NULL,
                data TEXT NOT NULL,
                ora TEXT NOT NULL,
                trattamento TEXT NOT NULL,
                data_creazione TEXT NOT NULL,
                device_id TEXT,
                stato_presenza TEXT DEFAULT 'Assente',
                codice_fiscale TEXT,
                codice_fiscale_2 TEXT
            )
        """))
        
        for col, col_type in [
            ("device_id", "TEXT"),
            ("stato_presenza", "TEXT DEFAULT 'Assente'"),
            ("codice_fiscale", "TEXT"),
            ("codice_fiscale_2", "TEXT")
        ]:
            try:
                conn.execute(text(f"ALTER TABLE prenotazioni ADD COLUMN IF NOT EXISTS {col} {col_type}"))
            except Exception:
                pass

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS banned_devices (
                device_id TEXT PRIMARY KEY
            )
        """))

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS utenti (
                id SERIAL PRIMARY KEY,
                nome TEXT NOT NULL,
                cognome TEXT NOT NULL,
                codice_fiscale TEXT NOT NULL UNIQUE,
                password_salt TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                data_registrazione TEXT NOT NULL
            )
        """))

init_db()

# Stile CSS professionale basato sul colore #f2b3ff, ombreggiature e animazioni coordinate
st.markdown(
    """
    <style>
    /* Sfondo generale pulito basato su #f2b3ff */
    .stApp {
        background-color: #fdf5ff;
        font-family: 'Inter', sans-serif;
    }

    /* Container professionali con bordi arrotondati, sfumatura delicata e ombreggiature con animazione */
    div.stVerticalBlockBorderWrapper, div[data-testid="stVerticalBlockBorderWrapper"] {
        background: linear-gradient(135deg, #ffffff 0%, #fcf0ff 100%) !important;
        border: 1px solid #f2b3ff !important;
        border-radius: 20px !important;
        padding: 24px !important;
        box-shadow: 0 10px 30px rgba(242, 179, 255, 0.2) !important;
        transition: all 0.3s ease-in-out !important;
    }
    
    div[data-testid="stVerticalBlockBorderWrapper"]:hover {
        box-shadow: 0 15px 35px rgba(242, 179, 255, 0.35) !important;
        transform: translateY(-2px);
    }
    
    div[data-testid="stVerticalBlockBorderWrapper"] div {
        background-color: transparent !important;
    }
    
    /* Campi di input moderni */
    .stTextInput input, .stSelectbox > div > div, .stDateInput input, .stNumberInput input {
        background-color: #FFFFFF !important;
        border-radius: 10px !important;
        border: 1.5px solid #e0a3ff !important;
        padding: 10px 14px !important;
        transition: all 0.2s ease-in-out !important;
    }

    .stTextInput input:focus, .stSelectbox > div > div:focus, .stDateInput input:focus, .stNumberInput input:focus {
        border-color: #7b1fa2 !important;
        box-shadow: 0 0 0 3px rgba(123, 31, 162, 0.15) !important;
    }
    
    /* Pulsanti professionali con effetti di transizione e ombreggiatura */
    div.stButton > button, div.stDownloadButton > button, div.stFormSubmitButton > button {
        background: linear-gradient(135deg, #7b1fa2 0%, #4a148c 100%) !important;
        color: white !important;
        border-radius: 12px !important;
        font-size: 1.05rem !important;
        font-weight: 600 !important;
        border: none !important;
        width: 100% !important;
        padding: 12px 24px !important;
        margin-top: 8px !important;
        text-align: center !important;
        display: block !important;
        box-shadow: 0 4px 15px rgba(123, 31, 162, 0.3) !important;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
        cursor: pointer;
    }
    
    div.stButton > button:hover, div.stDownloadButton > button:hover, div.stFormSubmitButton > button:hover {
        background: linear-gradient(135deg, #6a1b9a 0%, #38006b 100%) !important;
        color: white !important;
        box-shadow: 0 6px 20px rgba(123, 31, 162, 0.45) !important;
        transform: translateY(-2px);
    }

    div.stButton > button:active, div.stFormSubmitButton > button:active {
        transform: translateY(0px);
        box-shadow: 0 2px 10px rgba(123, 31, 162, 0.3) !important;
    }

    /* Stile specifico per il pulsante secondario (Password dimenticata?) nella seconda colonna */
    div[data-testid="stColumn"]:nth-child(2) div.stFormSubmitButton > button {
        background: #fcf0ff !important;
        color: #4a148c !important;
        border: 1.5px solid #f2b3ff !important;
        box-shadow: 0 4px 15px rgba(242, 179, 255, 0.2) !important;
    }

    div[data-testid="stColumn"]:nth-child(2) div.stFormSubmitButton > button:hover {
        background: #f8e1ff !important;
        color: #4a148c !important;
        box-shadow: 0 6px 20px rgba(242, 179, 255, 0.35) !important;
        transform: translateY(-2px);
    }
    
    div[data-testid="stColumn"] div.stButton > button.btn-aggiorna {
        padding: 8px 16px !important;
        font-size: 0.9rem !important;
        width: auto !important;
        white-space: nowrap !important;
    }
    
    /* Tipografia e Titoli */
    h1, h2, h3, h4 {
        color: #4a148c !important;
        font-weight: 700 !important;
        letter-spacing: -0.5px;
        text-align: center;
    }
    
    /* Box informativo in stile pastello con #f2b3ff */
    .box-info-carino {
        background: linear-gradient(135deg, #fcf0ff 0%, #f8e1ff) !important;
        border: 1px solid #f2b3ff !important;
        border-radius: 14px !important;
        padding: 16px 20px !important;
        margin-bottom: 20px !important;
        text-align: center !important;
        color: #4a148c !important;
        font-size: 0.98rem !important;
        box-shadow: 0 4px 15px rgba(242, 179, 255, 0.2) !important;
    }
    
    /* Stile delle Tab di navigazione - Uniforme e a capsula */
    .stTabs, .stTabs [data-baseweb="tab-list"], .stTabs div {
        overflow: visible !important;
    }

    .stTabs [data-baseweb="tab-highlight"] {
        display: none !important;
    }

    .stTabs [data-baseweb="tab-list"] {
        display: flex !important;
        flex-wrap: wrap !important;
        justify-content: center !important;
        gap: 8px !important;
    }

    .stTabs [data-baseweb="tab"] {
        background-color: #fcf0ff;
        border-radius: 40px !important;
        color: #4a148c;
        font-weight: 600;
        padding: 10px 24px !important;
        text-align: center !important;
        font-size: 15px !important;
        border: 1.5px solid #f2b3ff !important;
        transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275) !important;
        flex: 1 1 auto !important;
    }

    .stTabs [data-baseweb="tab"]:hover {
        background-color: #f8e1ff;
        transform: translateY(-2px);
    }

    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #f2b3ff 0%, #d880ff) !important;
        color: #ffffff !important;
        border-color: #d880ff !important;
        border-radius: 40px !important;
        padding: 10px 24px !important;
        box-shadow: 0 12px 30px rgba(216, 128, 255, 0.55) !important;
        transform: translateY(-4px) scale(1.03) !important;
        z-index: 999 !important;
    }

    @media (max-width: 768px) {
        .stTabs [data-baseweb="tab"] {
            padding: 8px 14px !important;
            font-size: 13px !important;
            min-width: auto !important;
        }
        .stTabs [aria-selected="true"] {
            padding: 8px 14px !important;
        }
    }

    .stCaption, p {
        text-align: center;
    }

    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    </style>
""",
    unsafe_allow_html=True,
)


# Funzioni di supporto per la verifica del Codice Fiscale
def estrai_consonanti_vocali(testo):
    testo = testo.upper()
    consonanti = "".join([c for c in testo if c.isalpha() and c not in "AEIOU"])
    vocali = "".join([c for c in testo if c.isalpha() and c in "AEIOU"])
    return consonanti, vocali


def calcola_iniziali_cf(cognome, nome):
    c_cons, c_voc = estrai_consonanti_vocali(cognome)
    cognome_cf = (c_cons + c_voc + "XXX")[:3]
    
    n_cons, n_voc = estrai_consonanti_vocali(nome)
    if len(n_cons) >= 4:
        nome_cf = n_cons[0] + n_cons[2] + n_cons[3]
    else:
        nome_cf = (n_cons + n_voc + "XXX")[:3]
        
    return cognome_cf, nome_cf


# Tabelle ufficiali per il calcolo del carattere di controllo del Codice Fiscale
_VALORI_DISPARI = {
    "0": 1, "1": 0, "2": 5, "3": 7, "4": 9, "5": 13, "6": 15, "7": 17, "8": 19, "9": 21,
    "A": 1, "B": 0, "C": 5, "D": 7, "E": 9, "F": 13, "G": 15, "H": 17, "I": 19, "J": 21,
    "K": 2, "L": 4, "M": 18, "N": 20, "O": 11, "P": 3, "Q": 6, "R": 8, "S": 12, "T": 14,
    "U": 16, "V": 10, "W": 22, "X": 25, "Y": 24, "Z": 23,
}
_VALORI_PARI = {
    "0": 0, "1": 1, "2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7, "8": 8, "9": 9,
    "A": 0, "B": 1, "C": 2, "D": 3, "E": 4, "F": 5, "G": 6, "H": 7, "I": 8, "J": 9,
    "K": 10, "L": 11, "M": 12, "N": 13, "O": 14, "P": 15, "Q": 16, "R": 17, "S": 18, "T": 19,
    "U": 20, "V": 21, "W": 22, "X": 23, "Y": 24, "Z": 25,
}
_LETTERE_RESTO = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def calcola_carattere_controllo_cf(cf_15):
    totale = 0
    for i, carattere in enumerate(cf_15):
        posizione = i + 1
        if posizione % 2 != 0:
            totale += _VALORI_DISPARI[carattere]
        else:
            totale += _VALORI_PARI[carattere]
    return _LETTERE_RESTO[totale % 26]


def valida_codice_fiscale(nome, cognome, cf):
    cf = cf.strip().upper()
    regex_cf = r"^[A-Z]{6}[0-9]{2}[ABCDEHLMPRST][0-9]{2}[A-Z][0-9]{3}[A-Z]$"
    if not re.match(regex_cf, cf):
        return False, "Il formato del Codice Fiscale non è valido (deve essere di 16 caratteri alfanumerici corretti)."

    cog_esperato, nome_esperato = calcola_iniziali_cf(cognome, nome)
    if cf[:3] != cog_esperato:
        return False, f"Le prime 3 lettere del Codice Fiscale non corrispondono al cognome inserito ({cognome})."
    if cf[3:6] != nome_esperato:
        return False, f"Le lettere 4-6 del Codice Fiscale non corrispondono al nome inserito ({nome})."

    carattere_atteso = calcola_carattere_controllo_cf(cf[:15])
    if cf[15] != carattere_atteso:
        return False, "Il Codice Fiscale inserito non è corretto (carattere di controllo non valido). Ricontrolla di averlo digitato correttamente."

    return True, ""


# --- Funzioni di supporto per Account Utenti (Registrazione/Login/Recupero) ---
def hash_password(password, salt=None):
    if salt is None:
        salt = secrets.token_hex(16)
    pwd_hash = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"), 100_000
    ).hex()
    return salt, pwd_hash


def verifica_password(password, salt, pwd_hash_atteso):
    _, pwd_hash_calcolato = hash_password(password, salt)
    return secrets.compare_digest(pwd_hash_calcolato, pwd_hash_atteso)


def registra_utente(nome, cognome, cf, password):
    salt, pwd_hash = hash_password(password)
    data_reg = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    try:
        with engine.begin() as conn:
            res = conn.execute(
                text("SELECT id FROM utenti WHERE codice_fiscale = :cf"),
                {"cf": cf.upper()}
            ).fetchone()
            
            if res:
                return False, "Esiste già un utente registrato con questo Codice Fiscale."
            
            conn.execute(
                text("""
                    INSERT INTO utenti (nome, cognome, codice_fiscale, password_salt, password_hash, data_registrazione) 
                    VALUES (:nome, :cognome, :cf, :salt, :pwd_hash, :data_reg)
                """),
                {
                    "nome": nome.title(),
                    "cognome": cognome.title(),
                    "cf": cf.upper(),
                    "salt": salt,
                    "pwd_hash": pwd_hash,
                    "data_reg": data_reg
                }
            )
        return True, "Registrazione completata con successo!"
    except Exception as e:
        return False, str(e)


def login_utente(nome, cognome, password):
    try:
        with engine.begin() as conn:
            res = conn.execute(
                text("""
                    SELECT id, nome, cognome, codice_fiscale, password_salt, password_hash 
                    FROM utenti 
                    WHERE UPPER(nome) = :nome AND UPPER(cognome) = :cognome
                """),
                {"nome": nome.strip().upper(), "cognome": cognome.strip().upper()}
            ).fetchone()
            
            if not res:
                return None, "Utente non trovato."
                
            uid, u_nome, u_cognome, u_cf, salt, pwd_hash = res
            
            if verifica_password(password, salt, pwd_hash):
                return {
                    "id": uid,
                    "nome": u_nome,
                    "cognome": u_cognome,
                    "codice_fiscale": u_cf
                }, None
            else:
                return None, "Password errata."
    except Exception as e:
        return None, str(e)


def aggiorna_password_utente(nome, cognome, cf, nuova_password):
    try:
        with engine.begin() as conn:
            res = conn.execute(
                text("""
                    SELECT id FROM utenti 
                    WHERE UPPER(nome) = :nome AND UPPER(cognome) = :cognome AND UPPER(codice_fiscale) = :cf
                """),
                {
                    "nome": nome.strip().upper(),
                    "cognome": cognome.strip().upper(),
                    "cf": cf.strip().upper()
                }
            ).fetchone()
            
            if not res:
                return False, "Nessun account trovato con i dati inseriti (Nome, Cognome e Codice Fiscale non corrispondono)."
                
            uid = res[0]
            salt, pwd_hash = hash_password(nuova_password)
            
            conn.execute(
                text("UPDATE utenti SET password_salt = :salt, password_hash = :pwd_hash WHERE id = :id"),
                {"salt": salt, "pwd_hash": pwd_hash, "id": uid}
            )
        return True, "Password reimpostata con successo! Ora puoi effettuare il login."
    except Exception as e:
        return False, str(e)


def get_orari_per_data(data):
    if isinstance(data, str):
        d = datetime.strptime(data, "%Y-%m-%d").date()
    else:
        d = data
    weekday = d.weekday()
    if weekday == 5: # Sabato
        return ["09:00", "10:00", "11:00", "12:00", "15:00", "16:00", "17:00"]
    elif weekday == 6: # Domenica chiuso
        return []
    else: # Lunedì - Venerdì
        return [
            "09:00", "10:00", "11:00", "12:00",
            "15:00", "16:00", "17:00", "18:00", "19:00",
        ]


def get_client_device_id():
    if "device_id_internale" not in st.session_state:
        if "dev_id" in st.query_params and st.query_params["dev_id"].strip():
            st.session_state["device_id_internale"] = (
                f"device_{st.query_params['dev_id']}"
            )
        else:
            unique_id = str(uuid.uuid4()).replace("-", "")[:24]
            st.query_params["dev_id"] = unique_id
            st.session_state["device_id_internale"] = f"device_{unique_id}"
    return st.session_state["device_id_internale"]


def get_current_time_local():
    try:
        local_tz = ZoneInfo("Europe/Rome")
        return datetime.now(local_tz)
    except Exception:
        return datetime.now()


def genera_file_ics(nome_trattamento, data_str, ora_str):
    dt_inizio = datetime.strptime(f"{data_str} {ora_str}", "%Y-%m-%d %H:%M")
    dt_fine = dt_inizio + timedelta(minutes=50)
    
    fmt = "%Y%m%dT%H%M00"
    titolo_evento = f"Lola's Glam House: {nome_trattamento}"
    
    ics_content = f"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Lolas Glam House//Estetica//IT
CALSCALE:GREGORIAN
METHOD:PUBLISH
BEGIN:VEVENT
SUMMARY:{titolo_evento}
DESCRIPTION:Appuntamento presso Lola's Glam House.\\nTi ricordiamo di arrivare puntuale per il tuo trattamento.
LOCATION:Lola's Glam House
DTSTART:{dt_inizio.strftime(fmt)}
DTEND:{dt_fine.strftime(fmt)}
BEGIN:VALARM
TRIGGER:-PT60M
ACTION:DISPLAY
DESCRIPTION:Promemoria: Tra 1 ora hai il tuo appuntamento da Lola's Glam House!
END:VALARM
END:VEVENT
END:VCALENDAR"""
    return ics_content


@st.dialog("📜 Regolamento del Salone - Termini di Servizio")
def popup_regolamento():
    st.markdown(
        """
        Prima di completare la prenotazione, ti invitiamo a leggere attentamente il regolamento di Lola's Glam House:
        
        * ⏱️ **Durata Trattamento:** Varia in base al servizio scelto.
        * 🕒 **Puntualità:** Si raccomanda la massima puntualità.
        * 🧴 **Cura di sé:** Vi invitiamo a segnalare eventuali allergie, sensibilità o condizioni particolari prima dell'inizio.
        * 📵 **Cellulari:** Modalità silenziosa consigliata per godersi il relax.
        * ⏱️ **Disdette:** Preavviso minimo di 24 ore, in caso contrario l'appuntamento potrebbe essere conteggiato.
        """
    )
    st.markdown("---")
    if st.button("✅ Ho letto e accetto il regolamento", use_container_width=True):
        st.session_state["regolamento_accettato"] = True
        st.session_state["mostra_dialog_regolamento"] = False
        st.rerun()


logo_path = None
for possible_name in [
    "logo.png", "logo.PNG", "logo.jpg", "logo.jpeg", "logo.png.png",
]:
    if os.path.exists(possible_name):
        logo_path = possible_name
        break


# --- BARRA LATERALE (Admin & Logo) ---
if logo_path:
    st.sidebar.image(logo_path, use_container_width=True)

st.sidebar.title("🔐 Area Riservata (Admin)")

ADMIN_PASSWORD = st.secrets.get("admin_password", "PasswordDiFallbackSeNonImpostata")

if "admin_logged_in" not in st.session_state:
    st.session_state["admin_logged_in"] = False

if not st.session_state["admin_logged_in"]:
    admin_pass = st.sidebar.text_input(
        "Password Admin", type="password", key="admin_pwd_input"
    )
    if admin_pass == ADMIN_PASSWORD:
        st.session_state["admin_logged_in"] = True
        st.rerun()
    elif admin_pass != "":
        st.sidebar.error("Password errata!")

if st.session_state["admin_logged_in"]:
    st.sidebar.success("Accesso Admin attivo")
    if st.sidebar.button("🚪 Esci dall'Area Admin"):
        st.session_state["admin_logged_in"] = False
        st.rerun()


# --- VISTA 1: PANNELLO AMMINISTRATORE ---
if st.session_state["admin_logged_in"]:
    st.title("📊 Gestione Appuntamenti & Salone (Admin)")

    if st.button("🔄 Aggiorna Dati", key="btn_aggiorna_dati"):
        st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

    with st.container(border=True):
        st.subheader("📋 Elenco Prenotazioni & Codici Fiscali")
        df = pd.read_sql_query(
            "SELECT id, codice_fiscale, codice_fiscale_2, data, ora, trattamento, stato_presenza, device_id FROM prenotazioni ORDER BY data DESC, ora ASC",
            engine,
        )

        if not df.empty:
            st.dataframe(df, use_container_width=True)
        else:
            st.info("Nessuna prenotazione presente nel database.")

    with st.container(border=True):
        st.subheader("✅ Spunta Presenze Veloci & Codici Seduta")
        st.write(
            "Seleziona la data: i clienti partono di default come assenti. "
            "**Metti la spunta solo a chi si è presentato** e clicca salva per generare i codici seduta."
        )

        data_presenze = st.date_input(
            "Data da verificare", value=datetime.today(), key="data_presenze_input"
        )
        data_presenze_str = str(data_presenze)

        with engine.begin() as conn:
            appuntamenti_giorno = conn.execute(
                text("SELECT id, nome, trattamento, ora, stato_presenza FROM prenotazioni WHERE data = :data AND device_id != 'SYSTEM' ORDER BY ora ASC"),
                {"data": data_presenze_str}
            ).fetchall()

        if appuntamenti_giorno:
            with st.form("form_presenze"):
                st.markdown(
                    f"**Appuntamenti del {data_presenze.strftime('%d/%m/%Y')}:**"
                )
                st.markdown("---")

                presenze_dict = {}
                for (
                    app_id, nome_cli, tratt_cli, ora_cli, stato_attuale,
                ) in appuntamenti_giorno:
                    col_p1, col_p2 = st.columns([3, 2])
                    is_checked_default = stato_attuale == "Presente"

                    with col_p1:
                        is_presente = st.checkbox(
                            f"{ora_cli} - {nome_cli}",
                            value=is_checked_default,
                            key=f"pres_{app_id}",
                        )
                        st.markdown(
                            f"<div style='color: #666; font-size: 0.85em; margin-top: -8px; margin-left: 24px;'>{tratt_cli}</div>",
                            unsafe_allow_html=True,
                        )
                        presenze_dict[app_id] = (
                            "Presente" if is_presente else "Assente"
                        )

                    with col_p2:
                        if is_presente:
                            codice_seduta = f"SEDUTA-OK-{app_id}-{data_presenze_str}"
                            st.markdown(
                                f"<code style='color: #7b1fa2; font-weight: bold;'>{codice_seduta}</code>",
                                unsafe_allow_html=True,
                            )
                        else:
                            st.markdown(
                                "<span style='color: gray;'>Assente</span>",
                                unsafe_allow_html=True,
                            )

                    st.markdown("---")

                submit_presenze = st.form_submit_button(
                    "💾 Salva Presenze & Genera Codici"
                )
                if submit_presenze:
                    with engine.begin() as conn:
                        for app_id, nuovo_stato in presenze_dict.items():
                            conn.execute(
                                text("UPDATE prenotazioni SET stato_presenza = :stato WHERE id = :pid"),
                                {"stato": nuovo_stato, "pid": app_id}
                            )
                    st.success("Presenze salvate con successo!")
                    st.rerun()
        else:
            st.info("Nessun appuntamento cliente registrato per la data selezionata.")

        st.markdown("---")
        st.markdown("#### 📈 Riepilogo e Calcolo Totale Trattamenti (Gestionale)")
        if st.button("📊 Calcola Statistiche e Trattamenti Svolti per Cliente"):
            df_stat = pd.read_sql_query(
                """
                SELECT nome, 
                       COUNT(CASE WHEN stato_presenza = 'Presente' THEN 1 END) AS trattamenti_effettuati,
                       COUNT(CASE WHEN stato_presenza = 'Assente' THEN 1 END) AS trattamenti_assenze,
                       COUNT(*) AS totale_prenotazioni
                FROM prenotazioni 
                WHERE device_id != 'SYSTEM'
                GROUP BY nome
                ORDER BY trattamenti_effettuati DESC
            """,
                engine,
            )
            if not df_stat.empty:
                st.dataframe(df_stat, use_container_width=True)
                st.success("💡 Report calcolato con successo!")
            else:
                st.info("Nastro dati insufficiente per le statistiche.")

    with st.container(border=True):
        st.subheader("📷 QR Code Check-in Ingresso Salone")
        st.write(
            "Mostra o stampa questo QR code da posizionare all'ingresso del salone. "
            "Quando arriva la cliente potrà inquadrarlo per registrare la presenza."
        )

        components.html(
            """
        <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; background: #ffffff; padding: 20px; border-radius: 12px; border: 2px dashed #7b1fa2;">
            <h4 style="color: #4a148c; margin-bottom: 10px;">Inquadra per Check-in in Salone 💅</h4>
            <div id="qrcode" style="margin: 15px;"></div>
            <p style="font-size: 12px; color: #555; text-align: center;">Inquadra con la fotocamera dello smartphone all'arrivo in salone.</p>
        </div>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/qrious/4.0.2/qrious.min.js"></script>
        <script>
        (function() {
            var parentUrl = window.parent.location.href.split('?')[0];
            var checkinUrl = parentUrl + '?action=checkin';
            
            var qr = new QRious({
                element: document.createElement('canvas'),
                value: checkinUrl,
                size: 200
            });
            document.getElementById('qrcode').appendChild(qr.element);
        })();
        </script>
        """,
            height=320,
            width=None,
        )

    with st.container(border=True):
        st.subheader("🔓 Gestione Chiusure e Sblocchi Salone")
        st.write("Seleziona un giorno o un intervallo e gestisci la disponibilità.")

        col_bs1, col_bs2 = st.columns(2)
        with col_bs1:
            data_intervallo = st.date_input(
                "Data o Intervallo di Date",
                value=(datetime.today(), datetime.today()),
                min_value=datetime.today(),
                key="data_intervallo_input",
            )
        with col_bs2:
            modo_intervallo = st.radio(
                "Ambito",
                ["Tutta la giornata", "Orario specifico"],
                key="modo_intervallo_input",
            )

        ora_intervallo = None
        TUTTI_GLI_ORARI_ADMIN = [
            "09:00", "10:00", "11:00", "12:00",
            "15:00", "16:00", "17:00", "18:00", "19:00",
        ]
        if modo_intervallo == "Orario specifico":
            ora_intervallo = st.selectbox(
                "Seleziona Orario", TUTTI_GLI_ORARI_ADMIN, key="ora_intervallo_input"
            )

        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            btn_blocca = st.button("🔒 Blocca Selezionati")
        with col_btn2:
            btn_sblocca = st.button("🔓 Sblocca Selezionati")

        if btn_blocca or btn_sblocca:
            if isinstance(data_intervallo, tuple):
                if len(data_intervallo) == 2:
                    lista_date = pd.date_range(
                        start=data_intervallo[0], end=data_intervallo[1]
                    ).strftime("%Y-%m-%d")
                elif len(data_intervallo) == 1:
                    lista_date = [str(data_intervallo[0])]
                else:
                    lista_date = []
            else:
                lista_date = [str(data_intervallo)]

            ora_attuale_str = get_current_time_local().strftime("%Y-%m-%d %H:%M")

            with engine.begin() as conn:
                if btn_blocca:
                    for d_str in lista_date:
                        if modo_intervallo == "Tutta la giornata":
                            orari_giorno = get_orari_per_data(d_str)
                            for h in orari_giorno:
                                res = conn.execute(
                                    text("SELECT id FROM prenotazioni WHERE data = :d AND ora = :h"),
                                    {"d": d_str, "h": h}
                                ).fetchone()
                                if not res:
                                    conn.execute(
                                        text("INSERT INTO prenotazioni (nome, data, ora, trattamento, data_creazione, device_id, stato_presenza) VALUES (:n, :d, :o, :t, :dc, :di, :sp)"),
                                        {
                                            "n": "🔒 SALONE CHIUSO", "d": d_str, "o": h,
                                            "t": "Chiusura Admin", "dc": ora_attuale_str,
                                            "di": "SYSTEM", "sp": "Chiuso"
                                        }
                                    )
                        else:
                            res = conn.execute(
                                text("SELECT id FROM prenotazioni WHERE data = :d AND ora = :o"),
                                {"d": d_str, "o": ora_intervallo}
                            ).fetchone()
                            if not res:
                                conn.execute(
                                    text("INSERT INTO prenotazioni (nome, data, ora, trattamento, data_creazione, device_id, stato_presenza) VALUES (:n, :d, :o, :t, :dc, :di, :sp)"),
                                    {
                                        "n": "🔒 ORARIO CHIUSO", "d": d_str, "o": ora_intervallo,
                                        "t": "Chiusura Admin", "dc": ora_attuale_str,
                                        "di": "SYSTEM", "sp": "Chiuso"
                                    }
                                )
                    st.success("Blocco applicato con successo!")

                elif btn_sblocca:
                    for d_str in lista_date:
                        if modo_intervallo == "Tutta la giornata":
                            conn.execute(text("DELETE FROM prenotazioni WHERE data = :d"), {"d": d_str})
                        else:
                            if ora_intervallo:
                                conn.execute(
                                    text("DELETE FROM prenotazioni WHERE data = :d AND ora = :o"),
                                    {"d": d_str, "o": ora_intervallo}
                                )
                    st.success("Sblocco applicato con successo!")

            st.rerun()

    with st.container(border=True):
        st.subheader("🛡️ Gestione Spam, Sicurezza e Blacklist")

        col_sec1, col_sec2 = st.columns(2)
        with col_sec1:
            st.markdown("##### Elimina Prenotazione Singola")
            id_da_eliminare = st.number_input(
                "ID Prenotazione da eliminare",
                min_value=0, step=1, key="id_elimina_input",
            )
            if st.button("Elimina Singola Prenotazione"):
                if id_da_eliminare > 0:
                    with engine.begin() as conn:
                        conn.execute(text("DELETE FROM prenotazioni WHERE id = :id"), {"id": id_da_eliminare})
                    st.success(f"Prenotazione #{id_da_eliminare} eliminata!")
                    st.rerun()

        with col_sec2:
            st.markdown("##### Banna Utente Individuale")
            df_prenotazioni_attive = pd.read_sql_query(
                "SELECT id, nome, trattamento, device_id FROM prenotazioni WHERE device_id != 'SYSTEM'",
                engine,
            )

            if not df_prenotazioni_attive.empty:
                df_prenotazioni_attive["label"] = (
                    df_prenotazioni_attive["id"].astype(str)
                    + " - "
                    + df_prenotazioni_attive["nome"]
                    + " ("
                    + df_prenotazioni_attive["trattamento"]
                    + ")"
                )
                scelta_ban = st.selectbox(
                    "Seleziona utente da bannare",
                    df_prenotazioni_attive["label"].tolist(),
                    key="seleziona_ban_input",
                )
                if st.button("Banna Utente Selezionato"):
                    id_selezionato = int(scelta_ban.split(" - ")[0])
                    with engine.begin() as conn:
                        res = conn.execute(
                            text("SELECT device_id FROM prenotazioni WHERE id = :id"),
                            {"id": id_selezionato}
                        ).fetchone()
                        if res and res[0]:
                            dev_id_da_bannare = res[0]
                            conn.execute(
                                text("INSERT INTO banned_devices (device_id) VALUES (:dev_id) ON CONFLICT (device_id) DO NOTHING"),
                                {"dev_id": dev_id_da_bannare}
                            )
                            st.success("Utente bannato con successo!")
                    st.rerun()
            else:
                st.info("Nessuna prenotazione disponibile.")

        st.markdown("##### 📋 Blacklist Dispositivi")
        df_banned = pd.read_sql_query(
            """
            SELECT b.device_id, 
                   COALESCE(string_agg(DISTINCT p.nome, ', '), 'Nessun nome') AS nominativi_utilizzati
            FROM banned_devices b
            LEFT JOIN prenotazioni p ON b.device_id = p.device_id
            GROUP BY b.device_id
        """,
            engine,
        )

        if not df_banned.empty:
            st.dataframe(df_banned, use_container_width=True)
            dev_da_sbannare = st.selectbox(
                "Dispositivo da rimuovere dalla blacklist",
                df_banned["device_id"].tolist(),
                key="sbianca_device",
            )
            if st.button("Rimuovi Ban (Sbanna)"):
                with engine.begin() as conn:
                    conn.execute(
                        text("DELETE FROM banned_devices WHERE device_id = :dev_id"),
                        {"dev_id": dev_da_sbannare}
                    )
                st.success("Dispositivo rimosso dalla blacklist!")
                st.rerun()
        else:
            st.info("Nessun dispositivo in blacklist.")

    with st.container(border=True):
        st.subheader("👤 Gestione Account Registrati")
        st.write(
            "Qui trovi tutti gli account creati dalle clienti (Nome, Cognome, Codice Fiscale). "
            "Puoi eliminarne uno se richiesto."
        )

        df_utenti = pd.read_sql_query(
            "SELECT id, nome, cognome, codice_fiscale, data_registrazione FROM utenti ORDER BY data_registrazione DESC",
            engine,
        )

        if not df_utenti.empty:
            st.dataframe(df_utenti, use_container_width=True)

            df_utenti["label"] = (
                df_utenti["id"].astype(str)
                + " - "
                + df_utenti["nome"]
                + " "
                + df_utenti["cognome"]
                + " ("
                + df_utenti["codice_fiscale"]
                + ")"
            )
            scelta_utente_elimina = st.selectbox(
                "Seleziona account da eliminare",
                df_utenti["label"].tolist(),
                key="seleziona_utente_elimina_input",
            )
            conferma_eliminazione = st.checkbox(
                "Confermo di voler eliminare definitivamente questo account",
                key="conferma_elimina_utente_checkbox",
            )
            if st.button("🗑️ Elimina Account Selezionato"):
                if not conferma_eliminazione:
                    st.error("Devi prima confermare la casella qui sopra per procedere con l'eliminazione.")
                else:
                    id_utente_da_eliminare = int(scelta_utente_elimina.split(" - ")[0])
                    with engine.begin() as conn:
                        conn.execute(
                            text("DELETE FROM utenti WHERE id = :id"),
                            {"id": id_utente_da_eliminare}
                        )
                    st.success(f"Account #{id_utente_da_eliminare} eliminato con successo!")
                    st.rerun()
        else:
            st.info("Nessun account cliente registrato al momento.")


# --- VISTA 2: PAGINA PRINCIPALE CLIENTE ---
else:
    client_device_id = get_client_device_id()
    
    with engine.begin() as conn:
        is_banned = conn.execute(
            text("SELECT device_id FROM banned_devices WHERE device_id = :dev_id"),
            {"dev_id": client_device_id}
        ).fetchone()

    if is_banned:
        if logo_path:
            c1, c2, c3 = st.columns([1, 2, 1])
            with c2:
                st.image(logo_path, use_container_width=True)
        st.error("⛔ Accesso negato: questo dispositivo è stato bloccato.")
    else:
        if st.query_params.get("action") == "checkin":
            if logo_path:
                c1, c2, c3 = st.columns([1, 2, 1])
                with c2:
                    st.image(logo_path, use_container_width=True)

            st.title("📍 Check-in Ingresso Salone")
            
            current_dt = get_current_time_local()
            oggi_str = current_dt.strftime("%Y-%m-%d")
            current_time = current_dt.time()

            if "checkin_successo" in st.session_state:
                p_id, p_nome, p_tratt, p_ora, oggi_str = st.session_state[
                    "checkin_successo"
                ]
                st.balloons()
                with st.container(border=True):
                    st.markdown(f"### Ciao {p_nome}! 💅")
                    st.success("🎉 **Presenza registrata con successo!**")
                    st.write(
                        f"Ho registrato il tuo arrivo per il trattamento di **{p_tratt}** delle ore **{p_ora}**."
                    )
                    st.markdown("---")
                    st.markdown(f"**Il tuo Codice Seduta:**")
                    st.markdown(
                        f"<h3 style='color: #7b1fa2; text-align: center;'>`SEDUTA-OK-{p_id}-{oggi_str}`</h3>",
                        unsafe_allow_html=True,
                    )
            else:
                with st.container(border=True):
                    utente_già_loggato = st.session_state.get("utente_loggato", None)

                    if utente_già_loggato:
                        st.markdown(f"**Benvenuta, {utente_già_loggato['nome']} {utente_già_loggato['cognome']}! 💅**")
                        st.write("Clicca sul pulsante sottostante per confermare il tuo arrivo in salone.")
                        
                        with st.form("form_checkin_veloce"):
                            submit_checkin_veloce = st.form_submit_button("✅ Conferma la mia Presenza")

                            if submit_checkin_veloce:
                                cf_utente = utente_già_loggato["codice_fiscale"]

                                with engine.begin() as conn:
                                    appuntamenti_trovati = conn.execute(
                                        text("""
                                            SELECT id, nome, trattamento, ora, stato_presenza 
                                            FROM prenotazioni 
                                            WHERE data = :data 
                                              AND device_id != 'SYSTEM' 
                                              AND (UPPER(codice_fiscale) = :cf OR UPPER(codice_fiscale_2) = :cf)
                                        """),
                                        {"data": oggi_str, "cf": cf_utente}
                                    ).fetchall()

                                if not appuntamenti_trovati:
                                    st.error("❌ Nessuna prenotazione trovata a tuo nome per oggi.")
                                else:
                                    appuntamento_valido = None
                                    for (
                                        p_id, p_nome, p_tratt, p_ora, p_stato,
                                    ) in appuntamenti_trovati:
                                        ora_app = datetime.strptime(
                                            p_ora, "%H:%M"
                                        ).time()
                                        dt_app = datetime.combine(
                                            datetime.today(), ora_app
                                        )

                                        inizio_finestra = (
                                            dt_app - timedelta(minutes=45)
                                        ).time()
                                        fine_finestra = (
                                            dt_app + timedelta(minutes=30)
                                        ).time()

                                        if (
                                            inizio_finestra
                                            <= current_time
                                            <= fine_finestra
                                        ):
                                            appuntamento_valido = (
                                                p_id, p_nome, p_tratt, p_ora
                                            )
                                            break

                                    if appuntamento_valido:
                                        p_id, p_nome, p_tratt, p_ora = (
                                            appuntamento_valido
                                        )

                                        with engine.begin() as conn:
                                            conn.execute(
                                                text("UPDATE prenotazioni SET stato_presenza = 'Presente' WHERE id = :pid"),
                                                {"pid": p_id}
                                            )

                                        st.session_state["checkin_successo"] = (
                                            p_id, p_nome, p_tratt, p_ora, oggi_str,
                                        )
                                        st.rerun()
                                    else:
                                        st.error(
                                            "⏳ Il check-in è consentito solo nell'orario prossimo al tuo appuntamento."
                                        )
                    else:
                        st.markdown(
                            "**Benvenuta in salone! 💅 Inserisci i dati del tuo account per confermare l'arrivo:**"
                        )
                        with st.form("form_checkin_cliente_automatico"):
                            chk_nome = st.text_input("Nome *")
                            chk_cognome = st.text_input("Cognome *")
                            chk_password = st.text_input("Password dell'account *", type="password")
                            submit_checkin = st.form_submit_button(
                                "✅ Conferma la mia Presenza"
                            )

                            if submit_checkin:
                                chk_nome_clean = chk_nome.strip().title()
                                chk_cognome_clean = chk_cognome.strip().title()

                                if not chk_nome_clean or not chk_cognome_clean or not chk_password:
                                    st.error("Per favore, compila tutti i campi.")
                                else:
                                    utente_verificato, msg_err = login_utente(
                                        chk_nome_clean, chk_cognome_clean, chk_password
                                    )

                                    if not utente_verificato:
                                        st.error(f"❌ Credenziali non valide: {msg_err}")
                                    else:
                                        cf_utente = utente_verificato["codice_fiscale"]

                                        with engine.begin() as conn:
                                            appuntamenti_trovati = conn.execute(
                                                text("""
                                                    SELECT id, nome, trattamento, ora, stato_presenza 
                                                    FROM prenotazioni 
                                                    WHERE data = :data 
                                                      AND device_id != 'SYSTEM' 
                                                      AND (UPPER(codice_fiscale) = :cf OR UPPER(codice_fiscale_2) = :cf)
                                                """),
                                                {"data": oggi_str, "cf": cf_utente}
                                            ).fetchall()

                                        if not appuntamenti_trovati:
                                            st.error("❌ Nessuna prenotazione trovata a tuo nome per oggi.")
                                        else:
                                            appuntamento_valido = None
                                            for (
                                                p_id, p_nome, p_tratt, p_ora, p_stato,
                                            ) in appuntamenti_trovati:
                                                ora_app = datetime.strptime(
                                                    p_ora, "%H:%M"
                                                ).time()
                                                dt_app = datetime.combine(
                                                    datetime.today(), ora_app
                                                )

                                                inizio_finestra = (
                                                    dt_app - timedelta(minutes=45)
                                                ).time()
                                                fine_finestra = (
                                                    dt_app + timedelta(minutes=30)
                                                ).time()

                                                if (
                                                    inizio_finestra
                                                    <= current_time
                                                    <= fine_finestra
                                                ):
                                                    appuntamento_valido = (
                                                        p_id, p_nome, p_tratt, p_ora
                                                    )
                                                    break

                                            if appuntamento_valido:
                                                p_id, p_nome, p_tratt, p_ora = (
                                                    appuntamento_valido
                                                )

                                                with engine.begin() as conn:
                                                    conn.execute(
                                                        text("UPDATE prenotazioni SET stato_presenza = 'Presente' WHERE id = :pid"),
                                                        {"pid": p_id}
                                                    )

                                                st.session_state["checkin_successo"] = (
                                                    p_id, p_nome, p_tratt, p_ora, oggi_str,
                                                )
                                                st.rerun()
                                            else:
                                                st.error(
                                                    "⏳ Il check-in è consentito solo nell'orario prossimo al tuo appuntamento."
                                                )

            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("🏠 Torna alla Home principale"):
                if "checkin_successo" in st.session_state:
                    del st.session_state["checkin_successo"]
                st.query_params.clear()
                st.rerun()

            st.stop()

        # --- GATE DI ACCESSO: Login / Registrazione Account Cliente ---
        if "utente_loggato" not in st.session_state:
            if logo_path:
                c1, c2, c3 = st.columns([1, 2, 1])
                with c2:
                    st.image(logo_path, use_container_width=True)

            st.title("Lola's Glam House")
            st.write("**Estetica & Benessere**")
            st.markdown("#### 👤 Accedi al tuo account o registrati")
            st.markdown(
                """
                <div class="box-info-carino">
                    ✨ Accedi o Registrati per poter prenotare il tuo prossimo trattamento con pochi semplici click.
                </div>
                """,
                unsafe_allow_html=True,
            )

            tab_login, tab_registrazione = st.tabs(["🔑 Accedi", "📝 Registrati"])

            with tab_login:
                if st.session_state.get("vista_recupero", False):
                    st.markdown("<h5 style='text-align: center; color: #4a148c;'>🔑 Reimposta Password</h5>", unsafe_allow_html=True)
                    st.write("Inserisci Nome, Cognome, Codice Fiscale e la nuova password.")
                    with st.form("form_recupero_password"):
                        rec_nome = st.text_input("Nome *", key="rec_nome_input")
                        rec_cognome = st.text_input("Cognome *", key="rec_cognome_input")
                        rec_cf = st.text_input("Codice Fiscale *", key="rec_cf_input")
                        rec_nuova_pw = st.text_input("Nuova Password *", type="password", key="rec_nuova_pw_input")
                        rec_conf_pw = st.text_input("Conferma Nuova Password *", type="password", key="rec_conf_pw_input")
                        
                        col_r1, col_r2 = st.columns(2)
                        with col_r1:
                            submit_esegui_recupero = st.form_submit_button("Aggiorna Password", use_container_width=True)
                        with col_r2:
                            submit_torna_login = st.form_submit_button("Torna all'Accedi", use_container_width=True)
                            
                        if submit_torna_login:
                            st.session_state["vista_recupero"] = False
                            st.rerun()
                            
                        if submit_esegui_recupero:
                            if rec_nuova_pw != rec_conf_pw:
                                st.error("❌ Le password non coincidono.")
                            elif not rec_nome or not rec_cognome or not rec_cf or not rec_nuova_pw:
                                st.error("❌ Compila tutti i campi obbligatori.")
                            else:
                                successo, msg = aggiorna_password_utente(rec_nome, rec_cognome, rec_cf, rec_nuova_pw)
                                if successo:
                                    st.success(msg)
                                    st.session_state["vista_recupero"] = False
                                    st.rerun()
                                else:
                                    st.error(f"❌ {msg}")
                else:
                    with st.form("form_login_utente"):
                        login_nome = st.text_input("Nome *", key="login_nome_input")
                        login_cognome = st.text_input("Cognome *", key="login_cognome_input")
                        login_password = st.text_input(
                            "Password *", type="password", key="login_password_input"
                        )
                        
                        col_b1, col_b2 = st.columns(2)
                        with col_b1:
                            submit_login = st.form_submit_button("Accedi", use_container_width=True)
                        with col_b2:
                            submit_recupero_click = st.form_submit_button("Password dimenticata?", use_container_width=True)

                        if submit_login:
                            utente, msg_errore = login_utente(
                                login_nome, login_cognome, login_password
                            )
                            if utente:
                                st.session_state["utente_loggato"] = utente
                                st.rerun()
                            else:
                                st.error(f"❌ {msg_errore}")
                        elif submit_recupero_click:
                            st.session_state["vista_recupero"] = True
                            st.rerun()

            with tab_registrazione:
                with st.form("form_registrazione_utente"):
                    reg_nome = st.text_input("Nome *", key="reg_nome_input")
                    reg_cognome = st.text_input("Cognome *", key="reg_cognome_input")
                    reg_cf = st.text_input("Codice Fiscale *", key="reg_cf_input")
                    reg_password = st.text_input(
                        "Scegli una Password *", type="password", key="reg_password_input"
                    )
                    reg_password_conferma = st.text_input(
                        "Conferma Password *", type="password", key="reg_password_conferma_input"
                    )
                    submit_registrazione = st.form_submit_button("Crea Account")

                    if submit_registrazione:
                        if reg_password != reg_password_conferma:
                            st.error("❌ Le due password inserite non coincidono.")
                        else:
                            successo, msg = registra_utente(
                                reg_nome, reg_cognome, reg_cf, reg_password
                            )
                            if successo:
                                st.success(msg)
                            else:
                                st.error(f"❌ {msg}")

            st.stop()

        if logo_path:
            c1, c2, c3 = st.columns([1, 2, 1])
            with c2:
                st.image(logo_path, use_container_width=True)

        st.title("Lola's Glam House")
        st.markdown(
            f"""
            <p style="text-align: center;">
                <strong>Estetica & Benessere</strong> &nbsp;|&nbsp; Ciao,
                {st.session_state['utente_loggato']['nome']} 👋
            </p>
            """,
            unsafe_allow_html=True,
        )

        tab1, tab2, tab3 = st.tabs([
            "📅 Prenota",
            "ℹ️ Info Salone",
            "📜 Regolamento",
        ])

        if st.session_state.get("mostra_dialog_regolamento", False):
            popup_regolamento()

        if st.session_state.get("regolamento_accettato", False) and "pending_booking" in st.session_state:
            pb = st.session_state["pending_booking"]
            
            data_creazione_str = get_current_time_local().strftime("%Y-%m-%d %H:%M")
            with engine.begin() as conn:
                conn.execute(
                    text("INSERT INTO prenotazioni (nome, data, ora, trattamento, data_creazione, device_id, stato_presenza, codice_fiscale, codice_fiscale_2) VALUES (:n, :d, :o, :t, :dc, :di, :sp, :cf1, :cf2)"),
                    {
                        "n": pb["nome_completo"],
                        "d": str(pb["data_scelta"]),
                        "o": pb["ora_scelta"],
                        "t": pb["trattamento"],
                        "dc": data_creazione_str,
                        "di": pb["client_device_id"],
                        "sp": "Assente",
                        "cf1": pb["cf_principale"],
                        "cf2": pb["cf_secondario"],
                    }
                )

            ics_string = genera_file_ics(pb["trattamento"], str(pb["data_scelta"]), pb["ora_scelta"])
            data_formattata = pb["data_scelta"].strftime("%d/%m/%Y")
            
            st.session_state["booking_success_msg"] = (
                f"🎉 PRENOTAZIONE CONFERMATA!\n\nGrazie {pb['nome']} {pb['cognome']}, ti aspettiamo il {data_formattata} alle ore {pb['ora_scelta']} per il trattamento: {pb['trattamento']}."
            )
            st.session_state["ics_data"] = ics_string
            st.session_state["reset_form_flag"] = True
            
            del st.session_state["pending_booking"]
            st.session_state["regolamento_accettato"] = False
            st.rerun()

        # TAB 1: PRENOTAZIONE
        with tab1:
            st.markdown("### Modulo di Prenotazione")

            if st.session_state.get("reset_form_flag", False):
                if "nome_2_input" in st.session_state:
                    st.session_state["nome_2_input"] = ""
                if "cognome_2_input" in st.session_state:
                    st.session_state["cognome_2_input"] = ""
                if "cf_2_input" in st.session_state:
                    st.session_state["cf_2_input"] = ""
                st.session_state["reset_form_flag"] = False

            if "booking_success_msg" in st.session_state:
                st.success(st.session_state["booking_success_msg"])
                
                if "ics_data" in st.session_state:
                    st.markdown("---")
                    st.markdown(
                        """
                        <div style="background-color: #fcf0ff; padding: 22px; border-radius: 14px; border: 2px solid #7b1fa2; text-align: center; margin-bottom: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.05);">
                            <h3 style="color: #4a148c; margin-top: 0; font-size: 1.35rem;">📲 SALVA L'APPUNTAMENTO NEL TUO CALENDARIO</h3>
                            <p style="font-size: 1.05rem; color: #333; margin-bottom: 15px; line-height: 1.5;">
                                Clicca sul pulsante qui sotto per scaricare il file dell'evento. Bastano pochissimi secondi per salvarlo sul tuo telefono o computer!
                            </p>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
                    
                    st.download_button(
                        label="📅 Scarica e Salva in Calendario (.ics)",
                        data=st.session_state["ics_data"],
                        file_name="appuntamento_lolas_glam_house.ics",
                        mime="text/calendar",
                        use_container_width=True
                    )
                    
                    with st.expander("💡 Come faccio a salvarlo nel calendario del mio telefono o PC?"):
                        st.markdown("""
                        * **🍎 iPhone / iPad:** Tocca il file scaricato e seleziona **"Aggiungi a Calendario"** nel menu che compare.
                        * **🤖 Android:** Tocca la notifica di download appena completato (o apri il file dalla cartella Download) e l'app Calendario ti chiederà di confermare l'aggiunta.
                        * **💻 PC (Windows / Mac):** Fai un doppio clic sul file scaricato; si aprirà automaticamente il tuo programma di posta o calendario predefinito (Outlook o Apple Calendar) per memorizzarlo.
                        """)
                    
                    st.markdown("---")

                if st.button("⬅️ Torna Indietro / Effettua Nuova Prenotazione"):
                    del st.session_state["booking_success_msg"]
                    if "ics_data" in st.session_state:
                        del st.session_state["ics_data"]
                    st.rerun()
            else:
                with st.container(border=True):
                    utente_loggato = st.session_state["utente_loggato"]
                    nome = utente_loggato["nome"]
                    cognome = utente_loggato["cognome"]
                    codice_fiscale = utente_loggato["codice_fiscale"]

                    st.info(
                        f"📌 Stai prenotando come **{nome} {cognome}** "
                        f"(CF: {codice_fiscale})"
                    )

                    trattamento = st.selectbox(
                        "Seleziona Trattamento Estetico *",
                        [
                            "Manicure Semipermanente",
                            "Pedicure Estetico",
                            "Pulizia Viso Profonda",
                            "Laminazione Ciglia e Sopracciglia",
                            "Trattamento Viso Anti-age",
                            "Massaggio Corpo Relax",
                            "Trattamento di Coppia",
                        ],
                        key="trattamento_input",
                    )

                    nome_2 = ""
                    cognome_2 = ""
                    codice_fiscale_2 = ""
                    if trattamento == "Trattamento di Coppia":
                        st.markdown("---")
                        st.markdown("##### 👥 Dati Seconda Persona (Coppia)")
                        col_n4, col_n5, col_n6 = st.columns([2, 2, 3])
                        with col_n4:
                            nome_2 = st.text_input("Nome Seconda Persona *", key="nome_2_input")
                        with col_n5:
                            cognome_2 = st.text_input("Cognome Seconda Persona *", key="cognome_2_input")
                        with col_n6:
                            codice_fiscale_2 = st.text_input("Codice Fiscale 2ª Persona *", key="cf_2_input")

                    col1, col2 = st.columns(2)

                    with col1:
                        data_scelta = st.date_input(
                            "Seleziona Data *", min_value=datetime.today(), key="data_input"
                        )

                    with engine.begin() as conn:
                        prenotazioni_giorno = conn.execute(
                            text("SELECT ora, trattamento, codice_fiscale, codice_fiscale_2, device_id FROM prenotazioni WHERE data = :d"),
                            {"d": str(data_scelta)}
                        ).fetchall()

                    TUTTI_GLI_ORARI = get_orari_per_data(data_scelta)
                    current_datetime = get_current_time_local()
                    current_date = current_datetime.date()
                    current_time = current_datetime.time()

                    cf_curr = codice_fiscale.strip().upper() if codice_fiscale else ""
                    cf_curr_2 = codice_fiscale_2.strip().upper() if codice_fiscale_2 else ""

                    orari_disponibili = []
                    for h in TUTTI_GLI_ORARI:
                        posti_occupati = 0
                        slot_bloccato = False
                        utente_gia_prenotato = False

                        for p_ora, p_trattamento, p_cf1, p_cf2, p_dev in prenotazioni_giorno:
                            if p_ora == h:
                                if (
                                    p_trattamento in ("Chiusura Admin", "🔒 SALONE CHIUSO")
                                    or "CHIUSO" in p_trattamento
                                ):
                                    slot_bloccato = True
                                    break
                                
                                if p_dev == client_device_id:
                                    utente_gia_prenotato = True
                                if cf_curr and (p_cf1 == cf_curr or p_cf2 == cf_curr or p_cf1 == cf_curr_2 or p_cf2 == cf_curr_2):
                                    utente_gia_prenotato = True
                                if cf_curr_2 and (p_cf1 == cf_curr_2 or p_cf2 == cf_curr_2):
                                    utente_gia_prenotato = True

                                if p_trattamento == "Trattamento di Coppia":
                                    posti_occupati += 2
                                else:
                                    posti_occupati += 1

                        if slot_bloccato or utente_gia_prenotato:
                            continue

                        if trattamento == "Trattamento di Coppia":
                            if posti_occupati > 0:
                                continue
                        else:
                            if posti_occupati >= 2:
                                continue

                        if data_scelta == current_date:
                            slot_time = datetime.strptime(h, "%H:%M").time()
                            if slot_time <= current_time:
                                continue

                        orari_disponibili.append(h)

                    with col2:
                        if orari_disponibili:
                            ora_scelta = st.selectbox(
                                "Seleziona Ora *", orari_disponibili, key="ora_input"
                            )
                        else:
                            st.selectbox(
                                "Seleziona Ora *",
                                ["Tutto occupato / Chiuso / Già prenotato"],
                                disabled=True,
                                key="dis_ora_occupato",
                            )
                            ora_scelta = None

                    submitted = st.button("Conferma Prenotazione")

                if submitted:
                    nome = nome.strip().title()
                    cognome = cognome.strip().title()
                    codice_fiscale = codice_fiscale.strip().upper()
                    
                    if trattamento == "Trattamento di Coppia":
                        nome_2 = nome_2.strip().title()
                        cognome_2 = cognome_2.strip().title()
                        codice_fiscale_2 = codice_fiscale_2.strip().upper()

                    with engine.begin() as conn_check:
                        is_banned_now = conn_check.execute(
                            text("SELECT device_id FROM banned_devices WHERE device_id = :di"),
                            {"di": client_device_id}
                        ).fetchone()

                    cf_valido, cf_msg = valida_codice_fiscale(nome, cognome, codice_fiscale)
                    
                    cf_2_valido = True
                    cf_2_msg = ""
                    if trattamento == "Trattamento di Coppia":
                        cf_2_valido, cf_2_msg = valida_codice_fiscale(nome_2, cognome_2, codice_fiscale_2)

                    cf_principale = codice_fiscale.strip().upper()
                    cf_secondario = codice_fiscale_2.strip().upper() if trattamento == "Trattamento di Coppia" else None

                    with engine.begin() as conn_dupl:
                        gia_presente = conn_dupl.execute(
                            text("""SELECT id FROM prenotazioni 
                                   WHERE data = :d AND ora = :o 
                                     AND (device_id = :di OR UPPER(codice_fiscale) = :cfp OR UPPER(codice_fiscale_2) = :cfp 
                                          OR (:cfs IS NOT NULL AND (UPPER(codice_fiscale) = :cfs OR UPPER(codice_fiscale_2) = :cfs)))"""),
                            {
                                "d": str(data_scelta), "o": ora_scelta, 
                                "di": client_device_id, "cfp": cf_principale,
                                "cfs": cf_secondario
                            }
                        ).fetchone()

                    if is_banned_now:
                        st.error("⛔ Spiacenti, questo dispositivo è stato bloccato.")
                    elif not nome.strip() or not cognome.strip() or not codice_fiscale.strip():
                        st.error("Per favore inserisci nome, cognome e codice fiscale.")
                    elif not cf_valido:
                        st.error(f"❌ **Codice Fiscale non valido per {nome} {cognome}:** {cf_msg}")
                    elif trattamento == "Trattamento di Coppia" and (not nome_2.strip() or not cognome_2.strip() or not codice_fiscale_2.strip()):
                        st.error("Per favore inserisci tutti i dati anche per la seconda persona.")
                    elif trattamento == "Trattamento di Coppia" and not cf_2_valido:
                        st.error(f"❌ **Codice Fiscale non valido per la seconda persona ({nome_2} {cognome_2}):** {cf_2_msg}")
                    elif gia_presente:
                        st.error("⚠️ Hai già una prenotazione attiva in questo giorno e orario (oppure una delle partecipanti risulta già registrata nello stesso slot).")
                    elif not ora_scelta or "Tutto occupato" in ora_scelta or "Già prenotato" in ora_scelta:
                        st.error("Spiacenti, non ci sono orari disponibili per la data selezionata.")
                    else:
                        if trattamento == "Trattamento di Coppia":
                            nome_completo = f"{nome.strip()} {cognome.strip()} & {nome_2.strip()} {cognome_2.strip()}"
                        else:
                            nome_completo = f"{nome.strip()} {cognome.strip()}"

                        with engine.begin() as conn:
                            esistenti = conn.execute(
                                text("SELECT trattamento FROM prenotazioni WHERE data = :d AND ora = :o"),
                                {"d": str(data_scelta), "o": ora_scelta}
                            ).fetchall()

                        slot_occupato = False
                        posti_occupati = 0
                        for (p_trattamento,) in esistenti:
                            if (
                                p_trattamento in ("Chiusura Admin", "🔒 SALONE CHIUSO")
                                or "CHIUSO" in p_trattamento
                            ):
                                slot_occupato = True
                                break
                            elif p_trattamento == "Trattamento di Coppia":
                                posti_occupati += 2
                            else:
                                posti_occupati += 1

                        impossibile_prenotare = False
                        if slot_occupato:
                            impossibile_prenotare = True
                        elif trattamento == "Trattamento di Coppia" and posti_occupati > 0:
                            impossibile_prenotare = True
                        elif trattamento != "Trattamento di Coppia" and posti_occupati >= 2:
                            impossibile_prenotare = True

                        if impossibile_prenotare:
                            st.error("⚠️ Spiacenti, questo orario è stato appena occupato! Riprova con un altro orario.")
                        else:
                            st.session_state["pending_booking"] = {
                                "nome_completo": nome_completo,
                                "data_scelta": data_scelta,
                                "ora_scelta": ora_scelta,
                                "trattamento": trattamento,
                                "client_device_id": client_device_id,
                                "cf_principale": cf_principale,
                                "cf_secondario": cf_secondario,
                                "nome": nome,
                                "cognome": cognome
                            }
                            st.session_state["mostra_dialog_regolamento"] = True
                            st.rerun()

        # TAB 2: INFO SALONE
        with tab2:
            st.markdown("### ℹ️ Informazioni su Lola's Glam House")
            st.markdown(
                "Benvenuta nel salone di bellezza **Lola's Glam House**, il tuo spazio esclusivo dedicato alla cura, alla bellezza e al benessere di viso e corpo."
            )
            st.markdown("📍 **Indirizzo:** Via della Bellezza 12, Città")
            st.markdown(
                "📞 **Telefono / WhatsApp:** [+39 300 0000000](tel:+39300000000) o [Scrivici su WhatsApp](https://wa.me/39300000000)"
            )
            st.markdown(
                "📧 **Email:** [lolasglamhouse@outlook.it](mailto:lolasglamhouse@outlook.it)"
            )
            st.markdown(
                "📸 Seguici su [Instagram](https://www.instagram.com/lolasglamhouse/) per scoprire tutti i nostri lavori, promozioni e novità del salone!"
            )

            st.markdown("---")
            st.markdown("#### 📋 Trattamenti & Pacchetti")
            st.markdown("""
                * 🏷️ **Pacchetto Sposa / Evento:** Trattamenti viso e corpo personalizzati
                * 🏷️ **Carnet 5 Manicure:** Sconto speciale sui trattamenti unghie
                * 🏷️ **Promozione Mese:** Sconti dedicati ai trattamenti stagionali
                * 🏷️ **Servizi Singoli:** Disponibili su prenotazione tramite app
                """)

            st.markdown("---")
            st.markdown("#### 📱 Installa la Web App sullo Smartphone")
            st.markdown("""
                Puoi aggiungere questa applicazione alla schermata principale del tuo telefono per accedere velocemente alle prenotazioni:
                * **🍎 iPhone / iPad (Safari):** Tocca l'icona di condivisione nel menu in basso e seleziona **"Aggiungi alla schermata Home"**.
                * **🤖 Android (Chrome):** Tocca i tre puntini in alto a destra nel browser e seleziona **"Aggiungi a schermata Home"** o **"Installa app"**.
                """)

        # TAB 3: REGOLAMENTO
        with tab3:
            st.markdown("### 📜 Regolamento del Salone")
            st.markdown("""
                * ⏱️ **Durata Trattamento:** Varia in base al servizio scelto.
                * 🕒 **Puntualità:** Si raccomanda la massima puntualità.
                * 🧴 **Cura di sé:** Vi invitiamo a segnalare eventuali allergie, sensibilità o condizioni particolari prima dell'inizio.
                * 📵 **Cellulari:** Modalità silenziosa consigliata per godersi il relax.
                * ⏱️ **Disdette:** Preavviso minimo di 24 ore, in caso contrario l'appuntamento potrebbe essere conteggiato.
                """)

        # --- Footer: pulsante di logout, in basso a sinistra ---
        st.markdown("<br>", unsafe_allow_html=True)
        col_footer_1, col_footer_2 = st.columns([1, 3])
        with col_footer_1:
            if st.button("🚪 Esci", key="btn_logout_footer"):
                del st.session_state["utente_loggato"]
                st.rerun()
