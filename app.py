from datetime import datetime
import os
import sqlite3
from zoneinfo import ZoneInfo
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

# Configurazione Pagina
st.set_page_config(
    page_title="Postura & Pilates - Dott.ssa Roberta Sinagra",
    page_icon="🧘‍♀️",
    layout="centered",
)

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
    
    div.stButton > button {
        background-color: #D81B60 !important;
        color: white !important;
        border-radius: 10px !important;
        font-size: 1rem !important;
        font-weight: bold !important;
        border: none !important;
        width: 100% !important;
        padding: 10px 20px !important;
        margin-top: 5px !important;
    }
    
    div.stButton > button:hover {
        background-color: #C2185B !important;
    }
    
    h1, h2, h3 {
        color: #880E4F !important;
        text-align: center;
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


# Inizializzazione Database SQLite con supporto Device ID e Blacklist
def init_db():
    conn = sqlite3.connect("prenotazioni.db")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS prenotazioni (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            data TEXT NOT NULL,
            ora TEXT NOT NULL,
            trattamento TEXT NOT NULL,
            data_creazione TEXT NOT NULL,
            device_id TEXT
        )
    """)
    try:
        c.execute("ALTER TABLE prenotazioni ADD COLUMN device_id TEXT")
    except sqlite3.OperationalError:
        pass

    c.execute("""
        CREATE TABLE IF NOT EXISTS banned_devices (
            device_id TEXT PRIMARY KEY
        )
    """)
    conn.commit()
    conn.close()


init_db()


# Funzione per determinare gli orari in base al giorno della settimana
def get_orari_per_data(data):
    if isinstance(data, str):
        d = datetime.strptime(data, "%Y-%m-%d").date()
    else:
        d = data
    weekday = d.weekday()  # 0=Lun, ..., 5=Sab, 6=Dom
    if weekday == 5:  # Sabato (08:00 - 13:00)
        return ["08:00", "09:00", "10:00", "11:00", "12:00", "13:00"]
    elif weekday == 6:  # Domenica (Chiuso)
        return []
    else:  # Lunedì - Venerdì (08:00 - 19:00 no stop)
        return [
            "08:00",
            "09:00",
            "10:00",
            "11:00",
            "12:00",
            "13:00",
            "14:00",
            "15:00",
            "16:00",
            "17:00",
            "18:00",
            "19:00",
        ]


# Identificazione univoca persistente tramite LocalStorage con schermata di caricamento e anti-cache
def get_client_device_id():
    if "dev_id" not in st.query_params or not st.query_params["dev_id"].strip():
        components.html(
            """
        <div style="display: flex; justify-content: center; align-items: center; height: 100vh; background-color: #fff0f5;">
            <h3 style="color: #880E4F; font-family: sans-serif;">Caricamento studio in corso... 🧘‍♀️</h3>
        </div>
        <script>
        let devId = localStorage.getItem('pilates_dev_id');
        if (!devId) {
            devId = Math.random().toString(36).substring(2, 15) + Math.random().toString(36).substring(2, 15);
            localStorage.setItem('pilates_dev_id', devId);
        }
        if (!window.location.search.includes('dev_id=' + devId)) {
            window.location.href = window.location.pathname + '?dev_id=' + devId + '&_=' + new Date().getTime();
        }
        </script>
        """,
            height=650,
            width=None,
        )
        st.stop()
    return f"device_{st.query_params['dev_id']}"


# Cerca se esiste il file del logo
logo_path = None
for possible_name in [
    "logo.png",
    "logo.PNG",
    "logo.jpg",
    "logo.jpeg",
    "logo.png.png",
]:
    if os.path.exists(possible_name):
        logo_path = possible_name
        break


# --- BARRA LATERALE (Admin & Logo) ---
if logo_path:
    st.sidebar.image(logo_path, use_container_width=True)

st.sidebar.title("🔐 Area Riservata (Admin)")

ADMIN_PASSWORD = "MiaPassword2026!"

# Gestione dello stato di Login Admin
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

# Pulsante di Logout se l'admin è collegato
if st.session_state["admin_logged_in"]:
    st.sidebar.success("Accesso Admin attivo")
    if st.sidebar.button("🚪 Esci dall'Area Admin"):
        st.session_state["admin_logged_in"] = False
        st.rerun()


# --- VISTA 1: PANNELLO AMMINISTRATORE ---
if st.session_state["admin_logged_in"]:
    st.title("📊 Gestione Appuntamenti & Studio (Admin)")

    # 1. TABELLA APPUNTAMENTI
    with st.container(border=True):
        st.subheader("📋 Elenco Prenotazioni")
        conn = sqlite3.connect("prenotazioni.db")
        df = pd.read_sql_query(
            "SELECT id, nome, data, ora, trattamento, data_creazione, device_id FROM"
            " prenotazioni ORDER BY data DESC, ora ASC",
            conn,
        )
        conn.close()

        if not df.empty:
            st.dataframe(df, use_container_width=True)
        else:
            st.info("Nessuna prenotazione presente nel database.")

    # 2. SEZIONE CHIUSURE E SBLOCCHI STUDIO
    with st.container(border=True):
        st.subheader("🔒🔓 Gestione Chiusure e Sblocchi Studio")
        st.write(
            "Seleziona un giorno o un intervallo, scegli l'orario (o l'intera"
            " giornata) e clicca sul pulsante corrispondente."
        )

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
            "08:00",
            "09:00",
            "10:00",
            "11:00",
            "12:00",
            "13:00",
            "14:00",
            "15:00",
            "16:00",
            "17:00",
            "18:00",
            "19:00",
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

            conn = sqlite3.connect("prenotazioni.db")
            c = conn.cursor()

            if btn_blocca:
                for d_str in lista_date:
                    if modo_intervallo == "Tutta la giornata":
                        orari_giorno = get_orari_per_data(d_str)
                        for h in orari_giorno:
                            c.execute(
                                "SELECT id FROM prenotazioni WHERE data = ? AND ora = ?",
                                (d_str, h),
                            )
                            if not c.fetchone():
                                c.execute(
                                    "INSERT INTO prenotazioni (nome, data, ora, trattamento,"
                                    " data_creazione, device_id) VALUES (?, ?, ?, ?, ?, ?)",
                                    (
                                        "🔒 STUDIO CHIUSO",
                                        d_str,
                                        h,
                                        "Chiusura Admin",
                                        datetime.now().strftime("%Y-%m-%d %H:%M"),
                                        "SYSTEM",
                                    ),
                                )
                    else:
                        c.execute(
                            "SELECT id FROM prenotazioni WHERE data = ? AND ora = ?",
                            (d_str, ora_intervallo),
                        )
                        if not c.fetchone():
                            c.execute(
                                "INSERT INTO prenotazioni (nome, data, ora, trattamento,"
                                " data_creazione, device_id) VALUES (?, ?, ?, ?, ?, ?)",
                                (
                                    "🔒 ORARIO CHIUSO",
                                    d_str,
                                    ora_intervallo,
                                    "Chiusura Admin",
                                    datetime.now().strftime("%Y-%m-%d %H:%M"),
                                    "SYSTEM",
                                ),
                            )
                st.success("Blocco applicato con successo per le date selezionate!")

            elif btn_sblocca:
                for d_str in lista_date:
                    if modo_intervallo == "Tutta la giornata":
                        c.execute("DELETE FROM prenotazioni WHERE data = ?", (d_str,))
                    else:
                        if ora_intervallo:
                            c.execute(
                                "DELETE FROM prenotazioni WHERE data = ? AND ora = ?",
                                (d_str, ora_intervallo),
                            )
                st.success("Sblocco applicato con successo per le date selezionate!")

            conn.commit()
            conn.close()
            st.rerun()

    # 3. SEZIONE: ELIMINAZIONE SINGOLA, BAN MIRATO E BLACKLIST
    with st.container(border=True):
        st.subheader("🛡️ Gestione Spam, Sicurezza e Blacklist")

        col_sec1, col_sec2 = st.columns(2)
        with col_sec1:
            st.markdown("##### Elimina Prenotazione Singola")
            id_da_eliminare = st.number_input(
                "ID Prenotazione da eliminare",
                min_value=0,
                step=1,
                key="id_elimina_input",
            )
            if st.button("Elimina Singola Prenotazione"):
                if id_da_eliminare > 0:
                    conn = sqlite3.connect("prenotazioni.db")
                    c = conn.cursor()
                    c.execute("DELETE FROM prenotazioni WHERE id = ?", (id_da_eliminare,))
                    conn.commit()
                    conn.close()
                    st.success(
                        f"Prenotazione con ID {id_da_eliminare} eliminata con successo!"
                    )
                    st.rerun()

        with col_sec2:
            st.markdown("##### Banna Utente Individuale")
            conn_b = sqlite3.connect("prenotazioni.db")
            df_prenotazioni_attive = pd.read_sql_query(
                "SELECT id, nome, trattamento, device_id FROM prenotazioni WHERE"
                " device_id != 'SYSTEM'",
                conn_b,
            )
            conn_b.close()

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
                    "Seleziona utente/prenotazione da bannare",
                    df_prenotazioni_attive["label"].tolist(),
                    key="seleziona_ban_input",
                )
                if st.button("Banna Utente Selezionato"):
                    id_selezionato = int(scelta_ban.split(" - ")[0])
                    conn = sqlite3.connect("prenotazioni.db")
                    c = conn.cursor()
                    c.execute(
                        "SELECT device_id FROM prenotazioni WHERE id = ?",
                        (id_selezionato,),
                    )
                    res = c.fetchone()
                    if res and res[0]:
                        dev_id_da_bannare = res[0]
                        c.execute(
                            "INSERT OR IGNORE INTO banned_devices (device_id) VALUES (?)",
                            (dev_id_da_bannare,),
                        )
                        conn.commit()
                        st.success(
                            f"L'utente associato alla prenotazione #{id_selezionato}"
                            f" (Dispositivo: {dev_id_da_bannare}) è stato bannato con"
                            " successo!"
                        )
                    conn.close()
                    st.rerun()
            else:
                st.info(
                    "Nessuna prenotazione disponibile da cui ricavare l'utente da"
                    " bannare."
                )

        st.markdown("##### 📋 Blacklist Dispositivi & Nominativi Associati")
        conn = sqlite3.connect("prenotazioni.db")
        df_banned = pd.read_sql_query(
            """
            SELECT b.device_id, 
                   COALESCE(GROUP_CONCAT(DISTINCT p.nome), 'Nessun nome registrato') AS nominativi_utilizzati
            FROM banned_devices b
            LEFT JOIN prenotazioni p ON b.device_id = p.device_id
            GROUP BY b.device_id
        """,
            conn,
        )
        conn.close()

        if not df_banned.empty:
            st.dataframe(df_banned, use_container_width=True)
            dev_da_sbannare = st.selectbox(
                "Seleziona Dispositivo da rimuovere dalla blacklist",
                df_banned["device_id"].tolist(),
                key="sbianca_device",
            )
            if st.button("Rimuovi Ban (Sbanna)"):
                conn = sqlite3.connect("prenotazioni.db")
                c = conn.cursor()
                c.execute(
                    "DELETE FROM banned_devices WHERE device_id = ?", (dev_da_sbannare,)
                )
                conn.commit()
                conn.close()
                st.success(f"Dispositivo rimosso dalla blacklist con successo!")
                st.rerun()
        else:
            st.info("Nessun dispositivo presente nella blacklist.")


# --- VISTA 2: PAGINA PRINCIPALE CLIENTE ---
else:
    # Controllo preventivo se il dispositivo corrente è bannato
    client_device_id = get_client_device_id()
    conn = sqlite3.connect("prenotazioni.db")
    c = conn.cursor()
    c.execute(
        "SELECT device_id FROM banned_devices WHERE device_id = ?",
        (client_device_id,),
    )
    is_banned = c.fetchone()
    conn.close()

    if is_banned:
        if logo_path:
            c1, c2, c3 = st.columns([1, 2, 1])
            with c2:
                st.image(logo_path, use_container_width=True)
        st.error(
            "⛔ Accesso negato: questo dispositivo è stato bloccato per"
            " violazione delle regole del servizio."
        )
    else:
        if logo_path:
            c1, c2, c3 = st.columns([1, 2, 1])
            with c2:
                st.image(logo_path, use_container_width=True)

        st.title("Postura & Pilates")
        st.write("**Dott.ssa Roberta Sinagra**")

        tab1, tab2, tab3, tab4 = st.tabs([
            "📅 Prenota",
            "ℹ️ Info Studio",
            "📍 Dove Siamo",
            "📜 Regolamento",
        ])

        # TAB 1: PRENOTAZIONE
        with tab1:
            st.markdown("### Modulo di Prenotazione")

            if st.session_state.get("reset_nome_flag", False):
                st.session_state["nome_input"] = ""
                st.session_state["reset_nome_flag"] = False

            if "booking_success_msg" in st.session_state:
                st.success(st.session_state["booking_success_msg"])
                del st.session_state["booking_success_msg"]

            with st.container(border=True):
                nome = st.text_input("Nome e Cognome *", key="nome_input")
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

                col1, col2 = st.columns(2)

                with col1:
                    data_scelta = st.date_input(
                        "Seleziona Data *", min_value=datetime.today(), key="data_input"
                    )

                conn = sqlite3.connect("prenotazioni.db")
                c = conn.cursor()
                c.execute(
                    "SELECT ora, trattamento FROM prenotazioni WHERE data = ?",
                    (str(data_scelta),),
                )
                prenotazioni_giorno = c.fetchall()
                conn.close()

                TUTTI_GLI_ORARI = get_orari_per_data(data_scelta)

                try:
                    local_tz = ZoneInfo("Europe/Rome")
                    current_datetime = datetime.now(local_tz)
                except Exception:
                    current_datetime = datetime.now()

                current_date = current_datetime.date()
                current_time = current_datetime.time()

                orari_disponibili = []
                for h in TUTTI_GLI_ORARI:
                    posti_occupati = 0
                    slot_bloccato = False

                    for p_ora, p_trattamento in prenotazioni_giorno:
                        if p_ora == h:
                            if (
                                p_trattamento in ("Chiusura Admin", "🔒 STUDIO CHIUSO")
                                or "CHIUSO" in p_trattamento
                            ):
                                slot_bloccato = True
                                break
                            elif p_trattamento == "Pilates Duetto (in coppia)":
                                posti_occupati += 2
                            else:
                                posti_occupati += 1

                    if slot_bloccato:
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
                            ["Tutto occupato / Chiuso"],
                            disabled=True,
                            key="dis_ora_occupato",
                        )
                        ora_scelta = None

                submitted = st.button("Conferma Prenotazione")

            if submitted:
                conn_check = sqlite3.connect("prenotazioni.db")
                c_check = conn_check.cursor()
                c_check.execute(
                    "SELECT device_id FROM banned_devices WHERE device_id = ?",
                    (client_device_id,),
                )
                is_banned_now = c_check.fetchone()
                conn_check.close()

                if is_banned_now:
                    st.error(
                        "⛔ Spiacenti, questo dispositivo è stato bloccato. Impossibile"
                        " completare la prenotazione."
                    )
                elif not nome.strip():
                    st.error("Per favore inserisci il tuo nome e cognome.")
                elif not ora_scelta or "Tutto occupato" in ora_scelta:
                    st.error(
                        "Spiacenti, non ci sono orari disponibili o lo studio è"
                        " chiuso per la data selezionata."
                    )
                else:
                    conn = sqlite3.connect("prenotazioni.db")
                    c = conn.cursor()
                    c.execute(
                        "SELECT trattamento FROM prenotazioni WHERE data = ? AND ora = ?",
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
                        st.error(
                            "⚠️ Spiacenti, questo orario non ha più disponibilità per il"
                            " trattamento scelto (potrebbe essere stato appena occupato)!"
                            " Riprova con un altro orario."
                        )
                        conn.close()
                    else:
                        c.execute(
                            "INSERT INTO prenotazioni (nome, data, ora, trattamento,"
                            " data_creazione, device_id) VALUES (?, ?, ?, ?, ?, ?)",
                            (
                                nome,
                                str(data_scelta),
                                ora_scelta,
                                trattamento,
                                datetime.now().strftime("%Y-%m-%d %H:%M"),
                                client_device_id,
                            ),
                        )
                        conn.commit()
                        conn.close()

                        data_formattata = data_scelta.strftime("%d/%m/%Y")
                        st.session_state["booking_success_msg"] = (
                            f"🎉 PRENOTAZIONE CONFERMATA!\n\nGrazie {nome}, ti aspettiamo il"
                            f" {data_formattata} alle ore {ora_scelta} per {trattamento}."
                        )
                        st.session_state["reset_nome_flag"] = True
                        st.rerun()

        # TAB 2: INFO STUDIO
        with tab2:
            st.markdown("### ℹ️ Informazioni sullo Studio")
            st.write(
                "Benvenuti nello studio della **Dott.ssa Roberta Sinagra**,"
                " specializzato in Posturologia e Pilates."
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
            st.markdown("#### 📱 Installa la Web App sul tuo Smartphone")
            st.markdown("""
                Puoi aggiungere questa applicazione alla schermata principale del tuo telefono per accedere velocemente alle prenotazioni, proprio come una normale app:
                * **🍎 iPhone / iPad (Safari):** Tocca l'icona di condivisione (il quadrato con la freccia verso l'alto) nel menu in basso e seleziona **"Aggiungi alla schermata Home"**.
                * **🤖 Android (Chrome):** Tocca i tre puntini in alto a destra nel browser e seleziona **"Aggiungi a schermata Home"** o **"Installa app"**.
                """)

        # TAB 3: DOVE SIAMO
        with tab3:
            st.markdown("### 📍 Dove Siamo & Contatti")
            st.write("📍 **Indirizzo:** Inserisci qui l'indirizzo dello studio")
            st.markdown(
                "📞 **Telefono / WhatsApp:** [+39 379"
                " 2073118](tel:+393792073118) o [Scrivici su"
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
                * ⏱️ **Disdette:** Preavviso minimo di 24 ore.
                """)
