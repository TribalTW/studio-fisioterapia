from datetime import datetime
import os
import sqlite3
import uuid
from zoneinfo import ZoneInfo
import pandas as pd
import streamlit as st

# Configurazione Pagina
st.set_page_config(
    page_title="Postura & Pilates - Dott.ssa Roberta Sinagra",
    page_icon="🧘‍♀️",
    layout="centered",
)

# Stile CSS con riquadro personalizzato (#fca4c3) sia per il cliente che per l'admin
st.markdown(
    """
    <style>
    /* Forzatura assoluta dello sfondo per tutti i contenitori con bordo (Client e Admin uguali) */
    div.stVerticalBlockBorderWrapper, div[data-testid="stVerticalBlockBorderWrapper"] {
        background-color: #fca4c3 !important;
        border: 1px solid #e882a4 !important;
        border-radius: 16px !important;
        padding: 20px !important;
    }
    
    /* Rende trasparenti i blocchi interni ai box colorati */
    div[data-testid="stVerticalBlockBorderWrapper"] div {
        background-color: transparent !important;
    }
    
    /* Campi di testo, selezioni e selettore data con sfondo bianco */
    .stTextInput input, .stSelectbox > div > div, .stDateInput input, .stNumberInput input {
        background-color: #FFFFFF !important;
        border-radius: 8px !important;
        border: 1px solid #E0E0E0 !important;
    }
    
    /* Pulsanti in rosa magenta originale */
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
    
    /* Titoli in rosa scuro */
    h1, h2, h3 {
        color: #880E4F !important;
        text-align: center;
    }
    
    /* Centra i sottotitoli */
    .stCaption, p {
        text-align: center;
    }
    
    /* Nasconde menu standard Streamlit */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    </style>
""",
    unsafe_allow_html=True,
)


# Inizializzazione Database SQLite con supporto IP e Ban
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
            ip TEXT
        )
    """)
  try:
    c.execute("ALTER TABLE prenotazioni ADD COLUMN ip TEXT")
  except sqlite3.OperationalError:
    pass

  c.execute("""
        CREATE TABLE IF NOT EXISTS banned_ips (
            ip TEXT PRIMARY KEY
        )
    """)
  conn.commit()
  conn.close()


init_db()


# Funzione avanzata per ricavare l'IP del client (con ID persistente per test in locale)
def get_client_ip():
  ip = "127.0.0.1"
  try:
    if hasattr(st, "context") and hasattr(st.context, "headers"):
      forwarded = st.context.headers.get("X-Forwarded-For", "")
      if forwarded:
        ip = forwarded.split(",")[0].strip()
      else:
        remote_addr = st.context.headers.get("Remote-Addr", "")
        if remote_addr:
          ip = remote_addr
  except Exception:
    pass

  # Se siamo in locale, usa i query params per mantenere lo stesso ID stabile sul browser del telefono
  if ip == "127.0.0.1":
    if "dev_id" not in st.query_params:
      st.query_params["dev_id"] = str(uuid.uuid4())[:8]
    return f"local_device_{st.query_params['dev_id']}"

  return ip


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


# --- VISTA 1: PANNELLO AMMINISTRATORE (Con box coordinati) ---
if st.session_state["admin_logged_in"]:
  st.title("📊 Gestione Appuntamenti & Studio (Admin)")

  # 1. TABELLA APPUNTAMENTI
  with st.container(border=True):
    st.subheader("📋 Elenco Prenotazioni")
    conn = sqlite3.connect("prenotazioni.db")
    df = pd.read_sql_query(
        "SELECT id, nome, data, ora, trattamento, data_creazione, ip FROM"
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

    # Logica comune di estrazione date per Blocco/Sblocco
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
            for h in TUTTI_GLI_ORARI_ADMIN:
              c.execute(
                  "SELECT id FROM prenotazioni WHERE data = ? AND ora = ?",
                  (d_str, h),
              )
              if not c.fetchone():
                c.execute(
                    "INSERT INTO prenotazioni (nome, data, ora, trattamento,"
                    " data_creazione, ip) VALUES (?, ?, ?, ?, ?, ?)",
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
                  " data_creazione, ip) VALUES (?, ?, ?, ?, ?, ?)",
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
          "SELECT id, nome, trattamento, ip FROM prenotazioni WHERE ip !="
          " 'SYSTEM'",
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
          c.execute("SELECT ip FROM prenotazioni WHERE id = ?", (id_selezionato,))
          res = c.fetchone()
          if res and res[0]:
            ip_da_bannare = res[0]
            c.execute(
                "INSERT OR IGNORE INTO banned_ips (ip) VALUES (?)",
                (ip_da_bannare,),
            )
            conn.commit()
            st.success(
                f"L'utente associato alla prenotazione #{id_selezionato}"
                f" (Dispositivo: {ip_da_bannare}) è stato bannato con successo!"
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
        SELECT b.ip, 
               COALESCE(GROUP_CONCAT(DISTINCT p.nome), 'Nessun nome registrato') AS nominativi_utilizzati
        FROM banned_ips b
        LEFT JOIN prenotazioni p ON b.ip = p.ip
        GROUP BY b.ip
    """,
        conn,
    )
    conn.close()

    if not df_banned.empty:
      st.dataframe(df_banned, use_container_width=True)
      ip_da_sbannare = st.selectbox(
          "Seleziona Dispositivo/IP da rimuovere dalla blacklist",
          df_banned["ip"].tolist(),
          key="sbianca_ip",
      )
      if st.button("Rimuovi Ban (Sbanna)"):
        conn = sqlite3.connect("prenotazioni.db")
        c = conn.cursor()
        c.execute("DELETE FROM banned_ips WHERE ip = ?", (ip_da_sbannare,))
        conn.commit()
        conn.close()
        st.success(f"Dispositivo rimosso dalla blacklist con successo!")
        st.rerun()
    else:
      st.info("Nessun dispositivo presente nella blacklist.")


# --- VISTA 2: PAGINA PRINCIPALE CLIENTE ---
else:
  # Controllo preventivo se il client è bannato
  client_ip = get_client_ip()
  conn = sqlite3.connect("prenotazioni.db")
  c = conn.cursor()
  c.execute("SELECT ip FROM banned_ips WHERE ip = ?", (client_ip,))
  is_banned = c.fetchone()
  conn.close()

  if is_banned:
    st.error(
        "⛔ Accesso negato: il tuo indirizzo IP è stato bloccato per violazione"
        " delle regole del servizio."
    )
  else:
    # MOSTRA IL LOGO CENTRATO IN CIMA ALLA PAGINA
    if logo_path:
      c1, c2, c3 = st.columns([1, 2, 1])
      with c2:
        st.image(logo_path, use_container_width=True)

    st.title("Postura & Pilates")
    st.write("**Dott.ssa Roberta Sinagra**")

    # Schede di Navigazione
    tab1, tab2, tab3, tab4 = st.tabs([
        "📅 Prenota",
        "ℹ️ Info Studio",
        "📍 Dove Siamo",
        "📜 Regolamento",
    ])

    # TAB 1: PRENOTAZIONE DINAMICA E REATTIVA
    with tab1:
      st.markdown("### Modulo di Prenotazione")

      # RESET SELETTIVO: Pulisce solo il nome dopo la conferma
      if st.session_state.get("reset_nome_flag", False):
        st.session_state["nome_input"] = ""
        st.session_state["reset_nome_flag"] = False

      # Messaggio di conferma verde se presente
      if "booking_success_msg" in st.session_state:
        st.success(st.session_state["booking_success_msg"])
        del st.session_state["booking_success_msg"]

      # RIQUADRO ROSA NATIVO CLIENTE
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

        # DATA ED ORA AFFIANCATE IN DUE COLONNE
        col1, col2 = st.columns(2)

        with col1:
          data_scelta = st.date_input(
              "Seleziona Data *", min_value=datetime.today(), key="data_input"
          )

        # Calcolo disponibilità orari in base al trattamento e alla capienza (max 2 persone)
        conn = sqlite3.connect("prenotazioni.db")
        c = conn.cursor()
        c.execute(
            "SELECT ora, trattamento FROM prenotazioni WHERE data = ?",
            (str(data_scelta),),
        )
        prenotazioni_giorno = c.fetchall()
        conn.close()

        TUTTI_GLI_ORARI = [
            "08:00",
            "09:00",
            "10:00",
            "11:00",
            "15:00",
            "16:00",
            "17:00",
            "18:00",
            "19:00",
        ]

        # Ottiene l'orario attuale italiano
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

          # Regola capienza: se si sceglie coppia serve slot totalmente libero (0 posti occupati)
          # Se si sceglie individuale/altro servono meno di 2 posti occupati (< 2)
          if trattamento == "Pilates Duetto (in coppia)":
            if posti_occupati > 0:
              continue
          else:
            if posti_occupati >= 2:
              continue

          # Controllo orari passati nella giornata odierna
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
                ["Tutto occupato"],
                disabled=True,
                key="dis_ora_occupato",
            )
            ora_scelta = None

        submitted = st.button("Conferma Prenotazione")

      # Logica di salvataggio con controllo capienza e IP
      if submitted:
        if not nome.strip():
          st.error("Per favore inserisci il tuo nome e cognome.")
        elif not ora_scelta or ora_scelta == "Tutto occupato":
          st.error(
              "Spiacenti, tutti gli orari per questa data sono già occupati o"
              " passati."
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
                " data_creazione, ip) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    nome,
                    str(data_scelta),
                    ora_scelta,
                    trattamento,
                    datetime.now().strftime("%Y-%m-%d %H:%M"),
                    client_ip,
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
      st.write(
          "I nostri percorsi individuali e di coppia sono pensati per migliorare"
          " la postura, prevenire dolori e ritrovare il benessere del corpo."
      )

    # TAB 3: DOVE SIAMO
    with tab3:
      st.markdown("### 📍 Dove Siamo & Contatti")
      st.write("📍 **Indirizzo:** Inserisci qui l'indirizzo dello studio")
      st.write("📞 **Telefono / WhatsApp:** +39 333 0000000")
      st.write("✉️ **Email:** info@posturaepilates.it")

    # TAB 4: REGOLAMENTO STUDIO
    with tab4:
      st.markdown("### 📜 Regolamento dello Studio")
      st.write(
          "Per garantire un ambiente sereno, pulito e professionale a tutti i"
          " pazienti, vi preghiamo di prendere visione delle seguenti regole:"
      )

      st.markdown("""
            * 🕒 **Puntualità:** Si raccomanda di presentarsi circa 5 minuti prima dell'orario della seduta.
            * 🧦 **Abbigliamento e Calzini:** È obbligatorio l'uso di **calzini antiscivolo** durante tutte le lezioni.
            * 🧴 **Asciugamano:** Si richiede di portare un proprio asciugamano personale da stendere sui macchinari/tappetini.
            * 📵 **Cellulari:** Vi chiediamo di mantenere il telefono in modalità silenziosa per rispettare la concentrazione e il relax.
            * ⏱️ **Disdette:** Le disdette o gli spostamenti devono essere comunicati con almeno **24 ore di anticipo**. In caso contrario, la seduta verrà regolarmente conteggiata.
            """)
