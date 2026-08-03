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
from sqlalchemy import create_engine
from sqlalchemy import text

# Configurazione Pagina
st.set_page_config(
    page_title="Postura & Pilates - Dott.ssa Roberta Sinagra",
    page_icon="🧘‍♀️",
    layout="centered",
)

# Connessione a Supabase / PostgreSQL
@st.cache_resource
def get_db_engine():
    db_url = st.secrets["supabase"]["db_url"]
    return create_engine(db_url)

def get_db_connection():
    db_url = st.secrets["supabase"]["db_url"]
    return psycopg2.connect(db_url)

engine = get_db_engine()

# Stile CSS della pagina
st.markdown(
    """
    <style>
    div.stVerticalBlockBorderWrapper, div[data-testid="stVerticalBlockBorderWrapper"] {
        background-color: #fca4c3 !important;
        border: 1px solid #e882a4 !important;
        border-radius: 16px !important;
        padding: 20px !important;
    }
    
    div[data-testid="stVerticalBlockBorderWrapper"] div {
        background-color: transparent !important;
    }
    
    .stTextInput input, .stSelectbox > div > div, .stDateInput input, .stNumberInput input {
        background-color: #FFFFFF !important;
        border-radius: 8px !important;
        border: 1px solid #E0E0E0 !important;
    }
    
    div.stButton > button, div.stDownloadButton > button {
        background-color: #D81B60 !important;
        color: white !important;
        border-radius: 12px !important;
        font-size: 1.1rem !important;
        font-weight: bold !important;
        border: none !important;
        width: 100% !important;
        padding: 12px 20px !important;
        margin-top: 5px !important;
        text-align: center !important;
        display: block !important;
    }
    
    div.stButton > button:hover, div.stDownloadButton > button:hover {
        background-color: #C2185B !important;
        color: white !important;
    }
    
    div[data-testid="stColumn"] div.stButton > button.btn-aggiorna {
        padding: 6px 15px !important;
        font-size: 0.9rem !important;
        width: auto !important;
        white-space: nowrap !important;
    }
    
    h1, h2, h3, h4 {
        color: #880E4F !important;
        text-align: center;
    }
    
    .box-info-carino {
        background-color: #fff5f8 !important;
        border: 1px solid #f3b6cc !important;
        border-radius: 12px !important;
        padding: 14px 18px !important;
        margin-bottom: 18px !important;
        text-align: center !important;
        color: #880E4F !important;
        font-size: 0.95rem !important;
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


# --- Funzioni di supporto per Account Utenti (Registrazione/Login) ---
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
    # Generazione hash e salt (come già fai)
    salt, pwd_hash = hash_password(password)
    data_reg = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    try:
        # Usa il pool di SQLAlchemy: velocissimo!
        with engine.begin() as conn:
            # Controlla se esiste già
            res = conn.execute(
                text("SELECT id FROM utenti WHERE codice_fiscale = :cf"),
                {"cf": cf.upper()}
            ).fetchone()
            
            if res:
                return False, "Esiste già un utente registrato con questo Codice Fiscale."
            
            # Inserisce il nuovo utente
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
            
            # Verifica la password
            if verify_password(password, salt, pwd_hash):
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


# Inizializzazione Database PostgreSQL / Supabase
def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("""
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
    """)
    conn.commit()
    
    for col, col_type in [
        ("device_id", "TEXT"),
        ("stato_presenza", "TEXT DEFAULT 'Assente'"),
        ("codice_fiscale", "TEXT"),
        ("codice_fiscale_2", "TEXT")
    ]:
        try:
            c.execute(f"ALTER TABLE prenotazioni ADD COLUMN IF NOT EXISTS {col} {col_type}")
            conn.commit()
        except Exception:
            conn.rollback()

    c.execute("""
        CREATE TABLE IF NOT EXISTS banned_devices (
            device_id TEXT PRIMARY KEY
        )
    """)
    conn.commit()

    c.execute("""
        CREATE TABLE IF NOT EXISTS utenti (
            id SERIAL PRIMARY KEY,
            nome TEXT NOT NULL,
            cognome TEXT NOT NULL,
            codice_fiscale TEXT NOT NULL UNIQUE,
            password_salt TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            data_registrazione TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


init_db()


def get_orari_per_data(data):
    if isinstance(data, str):
        d = datetime.strptime(data, "%Y-%m-%d").date()
    else:
        d = data
    weekday = d.weekday()
    if weekday == 5:
        return ["08:00", "09:00", "10:00", "11:00", "12:00", "13:00"]
    elif weekday == 6:
        return []
    else:
        return [
            "08:00", "09:00", "10:00", "11:00", "12:00", "13:00",
            "14:00", "15:00", "16:00", "17:00", "18:00", "19:00",
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


# Funzione per generare il file ICS universale
def genera_file_ics(nome_trattamento, data_str, ora_str):
    dt_inizio = datetime.strptime(f"{data_str} {ora_str}", "%Y-%m-%d %H:%M")
    dt_fine = dt_inizio + timedelta(minutes=50)
    
    fmt = "%Y%m%dT%H%M00"
    titolo_evento = f"Pilates: {nome_trattamento} - Dott.ssa Roberta Sinagra"
    
    ics_content = f"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Postura e Pilates//Dott.ssa Roberta Sinagra//IT
CALSCALE:GREGORIAN
METHOD:PUBLISH
BEGIN:VEVENT
SUMMARY:{titolo_evento}
DESCRIPTION:Appuntamento di Postura & Pilates con la Dott.ssa Roberta Sinagra.\\nRicorda di portare i calzini antiscivolo e un asciugamano personale.
LOCATION:Studio Dott.ssa Roberta Sinagra
DTSTART:{dt_inizio.strftime(fmt)}
DTEND:{dt_fine.strftime(fmt)}
BEGIN:VALARM
TRIGGER:-PT60M
ACTION:DISPLAY
DESCRIPTION:Promemoria: Tra 1 ora hai la lezione di Pilates in studio!
END:VALARM
END:VEVENT
END:VCALENDAR"""
    return ics_content


# Pop-up modale (Dialog) per l'accettazione obbligatoria del regolamento
@st.dialog("📜 Regolamento dello Studio - Termini di Servizio")
def popup_regolamento():
    st.markdown(
        """
        Prima di completare la prenotazione, ti invitiamo a leggere attentamente il regolamento dello studio:
        
        * ⏱️ **Durata Lezione:** La lezione dura 50 minuti.
        * 🕒 **Puntualità:** Si raccomanda di presentarsi circa 5 minuti prima dell'orario della seduta.
        * 🧦 **Abbigliamento e Calzini:** È obbligatorio l'uso di **calzini antiscivolo** durante tutte le lezioni.
        * 🧴 **Asciugamano:** Si richiede di portare un proprio asciugamano personale.
        * 📵 **Cellulari:** Modalità silenziosa consigliata.
        * ⏱️ **Disdette:** Preavviso minimo di 24 ore, in caso contrario la lezione verrà comunque conteggiata.
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
    st.title("📊 Gestione Appuntamenti & Studio (Admin)")

    if st.button("🔄 Aggiorna Dati", key="btn_aggiorna_dati"):
        st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

    with st.container(border=True):
        st.subheader("📋 Elenco Prenotazioni & Codici Fiscali")
        df = pd.read_sql_query(
            "SELECT id, email, codice_fiscale, codice_fiscale_2, data, ora, tipo AS trattamento, stato_presenza, device_id FROM prenotazioni ORDER BY data DESC, ora ASC",
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

        conn = get_db_connection()
        c = conn.cursor()
        c.execute(
            "SELECT id, nome, trattamento, ora, stato_presenza FROM prenotazioni WHERE data = %s AND device_id != 'SYSTEM' ORDER BY ora ASC",
            (data_presenze_str,),
        )
        appuntamenti_giorno = c.fetchall()
        conn.close()

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
                                f"<code style='color: #D81B60; font-weight: bold;'>{codice_seduta}</code>",
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
                    # Utilizziamo SQLAlchemy in modo rapido e sicuro con engine.begin()
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
        st.markdown("#### 📈 Riepilogo e Calcolo Totale Sedute (Gestionale)")
        if st.button("📊 Calcola Statistiche e Sedute Svolte per Cliente"):
            df_stat = pd.read_sql_query(
                """
                SELECT nome, 
                       COUNT(CASE WHEN stato_presenza = 'Presente' THEN 1 END) AS sedute_effettuate,
                       COUNT(CASE WHEN stato_presenza = 'Assente' THEN 1 END) AS sedute_assenze,
                       COUNT(*) AS totale_prenotazioni
                FROM prenotazioni 
                WHERE device_id != 'SYSTEM'
                GROUP BY nome
                ORDER BY sedute_effettuate DESC
            """,
                engine,
            )
            if not df_stat.empty:
                st.dataframe(df_stat, use_container_width=True)
                st.success("💡 Report calcolato con successo!")
            else:
                st.info("Nastro dati insufficiente per le statistiche.")

    with st.container(border=True):
        st.subheader("📷 QR Code Check-in Ingresso Studio")
        st.write(
            "Mostra o stampa questo QR code da posizionare all'ingresso dello studio. "
            "Quando arrivo il cliente potrà inquadrarlo per registrare la presenza."
        )

        components.html(
            """
        <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; background: #ffffff; padding: 20px; border-radius: 12px; border: 2px dashed #D81B60;">
            <h4 style="color: #880E4F; margin-bottom: 10px;">Inquadra per Check-in Studio 🧘‍♀️</h4>
            <div id="qrcode" style="margin: 15px;"></div>
            <p style="font-size: 12px; color: #555; text-align: center;">Inquadra con la fotocamera dello smartphone all'arrivo in studio.</p>
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
        st.subheader("🔒🔓 Gestione Chiusure e Sblocchi Studio")
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
            "08:00", "09:00", "10:00", "11:00", "12:00", "13:00",
            "14:00", "15:00", "16:00", "17:00", "18:00", "19:00",
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

            conn = get_db_connection()
            c = conn.cursor()
            ora_attuale_str = get_current_time_local().strftime("%Y-%m-%d %H:%M")

            if btn_blocca:
                for d_str in lista_date:
                    if modo_intervallo == "Tutta la giornata":
                        orari_giorno = get_orari_per_data(d_str)
                        for h in orari_giorno:
                            c.execute(
                                "SELECT id FROM prenotazioni WHERE data = %s AND ora = %s",
                                (d_str, h),
                            )
                            if not c.fetchone():
                                c.execute(
                                    "INSERT INTO prenotazioni (nome, data, ora, trattamento, data_creazione, device_id, stato_presenza) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                                    (
                                        "🔒 STUDIO CHIUSO", d_str, h,
                                        "Chiusura Admin",
                                        ora_attuale_str, "SYSTEM", "Chiuso",
                                    ),
                                )
                    else:
                        c.execute(
                            "SELECT id FROM prenotazioni WHERE data = %s AND ora = %s",
                            (d_str, ora_intervallo),
                        )
                        if not c.fetchone():
                            c.execute(
                                "INSERT INTO prenotazioni (nome, data, ora, trattamento, data_creazione, device_id, stato_presenza) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                                (
                                    "🔒 ORARIO CHIUSO", d_str, ora_intervallo,
                                    "Chiusura Admin",
                                    ora_attuale_str, "SYSTEM", "Chiuso",
                                ),
                            )
                st.success("Blocco applicato con successo!")

            elif btn_sblocca:
                for d_str in lista_date:
                    if modo_intervallo == "Tutta la giornata":
                        c.execute("DELETE FROM prenotazioni WHERE data = %s", (d_str,))
                    else:
                        if ora_intervallo:
                            c.execute(
                                "DELETE FROM prenotazioni WHERE data = %s AND ora = %s",
                                (d_str, ora_intervallo),
                            )
                st.success("Sblocco applicato con successo!")

            conn.commit()
            conn.close()
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
                    conn = get_db_connection()
                    c = conn.cursor()
                    c.execute("DELETE FROM prenotazioni WHERE id = %s", (id_da_eliminare,))
                    conn.commit()
                    conn.close()
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
                    conn = get_db_connection()
                    c = conn.cursor()
                    c.execute(
                        "SELECT device_id FROM prenotazioni WHERE id = %s",
                        (id_selezionato,),
                    )
                    res = c.fetchone()
                    if res and res[0]:
                        dev_id_da_bannare = res[0]
                        c.execute(
                            "INSERT INTO banned_devices (device_id) VALUES (%s) ON CONFLICT (device_id) DO NOTHING",
                            (dev_id_da_bannare,),
                        )
                        conn.commit()
                        st.success(f"Utente bannato con successo!")
                    conn.close()
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
                conn = get_db_connection()
                c = conn.cursor()
                c.execute(
                    "DELETE FROM banned_devices WHERE device_id = %s", (dev_da_sbannare,)
                )
                conn.commit()
                conn.close()
                st.success("Dispositivo rimosso dalla blacklist!")
                st.rerun()
        else:
            st.info("Nessun dispositivo in blacklist.")

    with st.container(border=True):
        st.subheader("👤 Gestione Account Registrati")
        st.write(
            "Qui trovi tutti gli account creati dai clienti (Nome, Cognome, Codice Fiscale). "
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
                    conn = get_db_connection()
                    c = conn.cursor()
                    c.execute("DELETE FROM utenti WHERE id = %s", (id_utente_da_eliminare,))
                    conn.commit()
                    conn.close()
                    st.success(f"Account #{id_utente_da_eliminare} eliminato con successo!")
                    st.rerun()
        else:
            st.info("Nessun account cliente registrato al momento.")


# --- VISTA 2: PAGINA PRINCIPALE CLIENTE ---
else:
    client_device_id = get_client_device_id()
    conn = get_db_connection()
    c = conn.cursor()
    c.execute(
        "SELECT device_id FROM banned_devices WHERE device_id = %s",
        (client_device_id,),
    )
    is_banned = c.fetchone()
    conn.close()

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

            st.title("📍 Check-in Ingresso Studio")
            
            current_dt = get_current_time_local()
            oggi_str = current_dt.strftime("%Y-%m-%d")
            current_time = current_dt.time()

            if "checkin_successo" in st.session_state:
                p_id, p_nome, p_tratt, p_ora, oggi_str = st.session_state[
                    "checkin_successo"
                ]
                st.balloons()
                with st.container(border=True):
                    st.markdown(f"### Ciao {p_nome}! 🧘‍♀️")
                    st.success("🎉 **Presenza registrata con successo!**")
                    st.write(
                        f"Ho registrato il tuo arrivo per la lezione di **{p_tratt}** delle ore **{p_ora}**."
                    )
                    st.markdown("---")
                    st.markdown(f"**Il tuo Codice Seduta:**")
                    st.markdown(
                        f"<h3 style='color: #D81B60; text-align: center;'>`SEDUTA-OK-{p_id}-{oggi_str}`</h3>",
                        unsafe_allow_html=True,
                    )
            else:
                with st.container(border=True):
                    # Controlla se l'utente è già loggato nella sessione principale
                    utente_già_loggato = st.session_state.get("utente_loggato", None)

                    if utente_già_loggato:
                        st.markdown(f"**Benvenuto/a, {utente_già_loggato['nome']} {utente_già_loggato['cognome']}! 🧘‍♀️**")
                        st.write("Clicca sul pulsante sottostante per confermare il tuo arrivo in studio.")
                        
                        with st.form("form_checkin_veloce"):
                            submit_checkin_veloce = st.form_submit_button("✅ Conferma la mia Presenza")

                            if submit_checkin_veloce:
                                cf_utente = utente_già_loggato["codice_fiscale"]

                                conn = get_db_connection()
                                c = conn.cursor()
                                c.execute(
                                    """
                                    SELECT id, nome, trattamento, ora, stato_presenza 
                                    FROM prenotazioni 
                                    WHERE data = %s 
                                      AND device_id != 'SYSTEM' 
                                      AND (UPPER(codice_fiscale) = %s OR UPPER(codice_fiscale_2) = %s)
                                    """,
                                    (oggi_str, cf_utente, cf_utente),
                                )
                                appuntamenti_trovati = c.fetchall()
                                conn.close()

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

                                        conn = get_db_connection()
                                        c = conn.cursor()
                                        c.execute(
                                            "UPDATE prenotazioni SET stato_presenza = 'Presente' WHERE id = %s",
                                            (p_id,),
                                        )
                                        conn.commit()
                                        conn.close()

                                        st.session_state["checkin_successo"] = (
                                            p_id, p_nome, p_tratt, p_ora, oggi_str,
                                        )
                                        st.rerun()
                                    else:
                                        st.error(
                                            "⏳ Il check-in è consentito solo nell'orario prossimo al tuo appuntamento."
                                        )
                    else:
                        # Se non è loggato, mostra il form con la richiesta password
                        st.markdown(
                            "**Benvenuto/a in studio! 🧘‍♀️ Inserisci i dati del tuo account per confermare l'arrivo:**"
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

                                        conn = get_db_connection()
                                        c = conn.cursor()
                                        c.execute(
                                            """
                                            SELECT id, nome, trattamento, ora, stato_presenza 
                                            FROM prenotazioni 
                                            WHERE data = %s 
                                              AND device_id != 'SYSTEM' 
                                              AND (UPPER(codice_fiscale) = %s OR UPPER(codice_fiscale_2) = %s)
                                            """,
                                            (oggi_str, cf_utente, cf_utente),
                                        )
                                        appuntamenti_trovati = c.fetchall()
                                        conn.close()

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

                                                conn = get_db_connection()
                                                c = conn.cursor()
                                                c.execute(
                                                    "UPDATE prenotazioni SET stato_presenza = 'Presente' WHERE id = %s",
                                                    (p_id,),
                                                )
                                                conn.commit()
                                                conn.close()

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

            st.title("Postura & Pilates")
            st.write("**Dott.ssa Roberta Sinagra**")
            st.markdown("#### 👤 Accedi al tuo account o registrati")
            st.markdown(
                """
                <div class="box-info-carino">
                    ✨ Crea un account una sola volta: alle prossime visite ti basterà accedere
                    con nome, cognome e password, senza dover reinserire il Codice Fiscale ogni volta.
                </div>
                """,
                unsafe_allow_html=True,
            )

            tab_login, tab_registrazione = st.tabs(["🔑 Accedi", "📝 Registrati"])

            with tab_login:
                with st.form("form_login_utente"):
                    login_nome = st.text_input("Nome *", key="login_nome_input")
                    login_cognome = st.text_input("Cognome *", key="login_cognome_input")
                    login_password = st.text_input(
                        "Password *", type="password", key="login_password_input"
                    )
                    submit_login = st.form_submit_button("Accedi")

                    if submit_login:
                        utente, msg_errore = login_utente(
                            login_nome, login_cognome, login_password
                        )
                        if utente:
                            st.session_state["utente_loggato"] = utente
                            st.rerun()
                        else:
                            st.error(f"❌ {msg_errore}")

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

        st.title("Postura & Pilates")
        st.markdown(
            f"""
            <p style="text-align: center;">
                <strong>Dott.ssa Roberta Sinagra</strong> &nbsp;|&nbsp; Ciao,
                {st.session_state['utente_loggato']['nome']} 👋
            </p>
            """,
            unsafe_allow_html=True,
        )

        tab1, tab2, tab3, tab4 = st.tabs([
            "📅 Prenota",
            "ℹ️ Info Studio",
            "📍 Dove Siamo",
            "📜 Regolamento",
        ])

        if st.session_state.get("mostra_dialog_regolamento", False):
            popup_regolamento()

        if st.session_state.get("regolamento_accettato", False) and "pending_booking" in st.session_state:
            pb = st.session_state["pending_booking"]
            
            conn = get_db_connection()
            c = conn.cursor()
            data_creazione_str = get_current_time_local().strftime("%Y-%m-%d %H:%M")
            c.execute(
                "INSERT INTO prenotazioni (nome, data, ora, trattamento, data_creazione, device_id, stato_presenza, codice_fiscale, codice_fiscale_2) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
                (
                    pb["nome_completo"],
                    str(pb["data_scelta"]),
                    pb["ora_scelta"],
                    pb["trattamento"],
                    data_creazione_str,
                    pb["client_device_id"],
                    "Assente",
                    pb["cf_principale"],
                    pb["cf_secondario"],
                ),
            )
            conn.commit()
            conn.close()

            ics_string = genera_file_ics(pb["trattamento"], str(pb["data_scelta"]), pb["ora_scelta"])
            data_formattata = pb["data_scelta"].strftime("%d/%m/%Y")
            
            st.session_state["booking_success_msg"] = (
                f"🎉 PRENOTAZIONE CONFERMATA!\n\nGrazie {pb['nome']} {pb['cognome']}, ti aspetto il {data_formattata} alle ore {pb['ora_scelta']} per {pb['trattamento']}."
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
                        <div style="background-color: #fff0f5; padding: 22px; border-radius: 14px; border: 2px solid #D81B60; text-align: center; margin-bottom: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.05);">
                            <h3 style="color: #880E4F; margin-top: 0; font-size: 1.35rem;">📲 SALVA L'APPUNTAMENTO NEL TUO CALENDARIO</h3>
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
                        file_name="appuntamento_pilates.ics",
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
                        "Seleziona Trattamento / Lezione *",
                        [
                            "Valutazione Posturale",
                            "Lezione Pilates Individuale",
                            "Pilates Duetto (in coppia)",
                            "Rieducazione Posturale Motorìa",
                        ],
                        key="trattamento_input",
                    )

                    nome_2 = ""
                    cognome_2 = ""
                    codice_fiscale_2 = ""
                    if trattamento == "Pilates Duetto (in coppia)":
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

                    conn = get_db_connection()
                    c = conn.cursor()
                    c.execute(
                        "SELECT ora, trattamento, codice_fiscale, codice_fiscale_2, device_id FROM prenotazioni WHERE data = %s",
                        (str(data_scelta),),
                    )
                    prenotazioni_giorno = c.fetchall()
                    conn.close()

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
                                    p_trattamento in ("Chiusura Admin", "🔒 STUDIO CHIUSO")
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

                                if p_trattamento == "Pilates Duetto (in coppia)":
                                    posti_occupati += 2
                                else:
                                    posti_occupati += 1

                        if slot_bloccato or utente_gia_prenotato:
                            continue

                        if trattamento == "Pilates Duetto (in coppia)":
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
                    
                    if trattamento == "Pilates Duetto (in coppia)":
                        nome_2 = nome_2.strip().title()
                        cognome_2 = cognome_2.strip().title()
                        codice_fiscale_2 = codice_fiscale_2.strip().upper()

                    conn_check = get_db_connection()
                    c_check = conn_check.cursor()
                    c_check.execute(
                        "SELECT device_id FROM banned_devices WHERE device_id = %s",
                        (client_device_id,),
                    )
                    is_banned_now = c_check.fetchone()
                    conn_check.close()

                    cf_valido, cf_msg = valida_codice_fiscale(nome, cognome, codice_fiscale)
                    
                    cf_2_valido = True
                    cf_2_msg = ""
                    if trattamento == "Pilates Duetto (in coppia)":
                        cf_2_valido, cf_2_msg = valida_codice_fiscale(nome_2, cognome_2, codice_fiscale_2)

                    cf_principale = codice_fiscale.strip().upper()
                    cf_secondario = codice_fiscale_2.strip().upper() if trattamento == "Pilates Duetto (in coppia)" else None

                    conn_dupl = get_db_connection()
                    c_dupl = conn_dupl.cursor()
                    c_dupl.execute(
                        """SELECT id FROM prenotazioni 
                           WHERE data = %s AND ora = %s 
                             AND (device_id = %s OR UPPER(codice_fiscale) = %s OR UPPER(codice_fiscale_2) = %s 
                                  OR (%s IS NOT NULL AND (UPPER(codice_fiscale) = %s OR UPPER(codice_fiscale_2) = %s)))""",
                        (
                            str(data_scelta), ora_scelta, 
                            client_device_id, cf_principale, cf_principale,
                            cf_secondario, cf_secondario, cf_secondario
                        )
                    )
                    gia_presente = c_dupl.fetchone()
                    conn_dupl.close()

                    if is_banned_now:
                        st.error("⛔ Spiacenti, questo dispositivo è stato bloccato.")
                    elif not nome.strip() or not cognome.strip() or not codice_fiscale.strip():
                        st.error("Per favore inserisci nome, cognome e codice fiscale.")
                    elif not cf_valido:
                        st.error(f"❌ **Codice Fiscale non valido per {nome} {cognome}:** {cf_msg}")
                    elif trattamento == "Pilates Duetto (in coppia)" and (not nome_2.strip() or not cognome_2.strip() or not codice_fiscale_2.strip()):
                        st.error("Per favore inserisci tutti i dati anche per la seconda persona.")
                    elif trattamento == "Pilates Duetto (in coppia)" and not cf_2_valido:
                        st.error(f"❌ **Codice Fiscale non valido per la seconda persona ({nome_2} {cognome_2}):** {cf_2_msg}")
                    elif gia_presente:
                        st.error("⚠️ Hai già una prenotazione attiva in questo giorno e orario (oppure uno dei partecipanti risulta già registrato nello stesso slot).")
                    elif not ora_scelta or "Tutto occupato" in ora_scelta or "Già prenotato" in ora_scelta:
                        st.error("Spiacenti, non ci sono orari disponibili per la data selezionata.")
                    else:
                        if trattamento == "Pilates Duetto (in coppia)":
                            nome_completo = f"{nome.strip()} {cognome.strip()} & {nome_2.strip()} {cognome_2.strip()}"
                        else:
                            nome_completo = f"{nome.strip()} {cognome.strip()}"

                        conn = get_db_connection()
                        c = conn.cursor()
                        c.execute(
                            "SELECT trattamento FROM prenotazioni WHERE data = %s AND ora = %s",
                            (str(data_scelta), ora_scelta),
                        )
                        esistenti = c.fetchall()

                        slot_occupato = False
                        posti_occupati = 0
                        for (p_trattamento,) in esistenti:
                            if (
                                p_trattamento in ("Chiusura Admin", "🔒 STUDIO CHIUSO")
                                or "CHIUSO" in p_trattamento
                            ):
                                slot_occupato = True
                                break
                            elif p_trattamento == "Pilates Duetto (in coppia)":
                                posti_occupati += 2
                            else:
                                posti_occupati += 1

                        impossibile_prenotare = False
                        if slot_occupato:
                            impossibile_prenotare = True
                        elif trattamento == "Pilates Duetto (in coppia)" and posti_occupati > 0:
                            impossibile_prenotare = True
                        elif trattamento != "Pilates Duetto (in coppia)" and posti_occupati >= 2:
                            impossibile_prenotare = True

                        if impossibile_prenotare:
                            st.error("⚠️ Spiacenti, questo orario è stato appena occupato! Riprova con un altro orario.")
                            conn.close()
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
                            conn.close()
                            st.rerun()

        # TAB 2: INFO STUDIO
        with tab2:
            st.markdown("### ℹ️ Informazioni sullo Studio")
            st.markdown(
                "Benvenuto/a nello studio della **Dott.ssa Roberta Sinagra**, specializzato in Posturologia e Pilates.\n\n"
                "📸 Seguimi su [Instagram](https://www.instagram.com/posturaepilates/) per rimanere sempre aggiornato/a su consigli posturali, esercizi e novità dello studio!"
            )

            st.markdown("---")
            st.markdown("#### 💳 Tipologie di Abbonamenti e Tariffe")
            st.markdown("""
                * 🏷️ **Abbonamento Trimestrale:** 3 mesi, 2 volte a settimana (massimo 3 recuperi)
                * 🏷️ **Abbonamento Mensile:** 1 mese, 2 volte a settimana (massimo 3 recuperi)
                * 🏷️ **Carnet 10 Lezioni:** 10 lezioni spendibili nell'arco dei 3 mesi
                * 🏷️ **Lezione Singola:** Ingresso singolo
                """)

            st.markdown("---")
            st.markdown("#### 📱 Installa la Web App sullo Smartphone")
            st.markdown("""
                Puoi aggiungere questa applicazione alla schermata principale del tuo telefono per accedere velocemente alle prenotazioni:
                * **🍎 iPhone / iPad (Safari):** Tocca l'icona di condivisione nel menu in basso e seleziona **"Aggiungi alla schermata Home"**.
                * **🤖 Android (Chrome):** Tocca i tre puntini in alto a destra nel browser e seleziona **"Aggiungi a schermata Home"** o **"Installa app"**.
                """)

        # TAB 3: DOVE SIAMO
        with tab3:
            st.markdown("### 📍 Dove Siamo & Contatti")
            st.write("📍 **Indirizzo:** Inserisci qui l'indirizzo dello studio")
            st.markdown(
                "📞 **Telefono / WhatsApp:** [+39 379"
                " 2073118](tel:+393792073118) o [Scrivimi su"
                " WhatsApp](https://wa.me/393792073118)"
            )
            st.markdown(
                "📧 **Email:**"
                " [posturaepilates@outlook.it](mailto:posturaepilates@outlook.it)"
            )

        # TAB 4: REGOLAMENTO
        with tab4:
            st.markdown("### 📜 Regolamento dello Studio")
            st.markdown("""
                * ⏱️ **Durata Lezione:** La lezione dura 50 minuti.
                * 🕒 **Puntualità:** Si raccomanda di presentarsi circa 5 minuti prima dell'orario della seduta.
                * 🧦 **Abbigliamento e Calzini:** È obbligatorio l'uso di **calzini antiscivolo** durante tutte le lezioni.
                * 🧴 **Asciugamano:** Si richiede di portare un proprio asciugamano personale.
                * 📵 **Cellulari:** Modalità silenziosa consigliata.
                * ⏱️ **Disdette:** Preavviso minimo di 24 ore, in caso contrario la lezione verrà comunque conteggiata.
                """)

        # --- Footer: pulsante di logout, in basso a sinistra ---
        st.markdown("<br>", unsafe_allow_html=True)
        col_footer_1, col_footer_2 = st.columns([1, 3])
        with col_footer_1:
            if st.button("🚪 Esci", key="btn_logout_footer"):
                del st.session_state["utente_loggato"]
                st.rerun()
