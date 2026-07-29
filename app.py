from datetime import datetime
import os
import sqlite3
import pandas as pd
import streamlit as st

# Configurazione Pagina
st.set_page_config(
    page_title="Postura & Pilates - Dott.ssa Roberta Sinagra",
    page_icon="🧘‍♀️",
    layout="centered",
)

# Stile CSS con forzatura mirata dello sfondo del riquadro
st.markdown(
    """
    <style>
    /* Forzatura assoluta dello sfondo rosa per il contenitore del modulo */
    div.stVerticalBlockBorderWrapper, div[data-testid="stVerticalBlockBorderWrapper"] {
        background-color: #FCE4EC !important;
        border: 1px solid #F8BBD0 !important;
        border-radius: 16px !important;
        padding: 20px !important;
    }
    
    /* Rende trasparenti i blocchi interni al box rosa */
    div[data-testid="stVerticalBlockBorderWrapper"] div {
        background-color: transparent !important;
    }
    
    /* Campi di testo, selezioni e selettore data con sfondo bianco */
    .stTextInput input, .stSelectbox > div > div, .stDateInput input {
        background-color: #FFFFFF !important;
        border-radius: 8px !important;
        border: 1px solid #E0E0E0 !important;
    }
    
    /* Pulsante di conferma rosa magenta */
    div.stButton > button {
        background-color: #D81B60 !important;
        color: white !important;
        border-radius: 10px !important;
        font-size: 1.1rem !important;
        font-weight: bold !important;
        border: none !important;
        width: 100% !important;
        padding: 12px 20px !important;
        margin-top: 10px !important;
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


# Inizializzazione Database SQLite
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
            data_creazione TEXT NOT NULL
        )
    """)
  conn.commit()
  conn.close()


init_db()

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
  st.title("📊 Gestione Appuntamenti (Admin)")

  conn = sqlite3.connect("prenotazioni.db")
  df = pd.read_sql_query(
      "SELECT id, nome, data, ora, trattamento, data_creazione FROM"
      " prenotazioni ORDER BY data DESC, ora ASC",
      conn,
  )
  conn.close()

  if not df.empty:
    st.dataframe(df, use_container_width=True)
  else:
    st.info("Nessuna prenotazione presente nel database.")

  st.markdown("---")
  st.subheader("🔒 Gestione Chiusure / Blocchi Studio")
  st.write(
      "Seleziona una data per bloccare l'intera giornata o un orario"
      " specifico."
  )

  col_b1, col_b2 = st.columns(2)
  with col_b1:
    data_blocco = st.date_input(
        "Data da gestire", min_value=datetime.today(), key="data_blocco_input"
    )
  with col_b2:
    tipo_blocco = st.radio(
        "Tipo di blocco",
        ["Tutta la giornata", "Orario specifico"],
        key="tipo_blocco_input",
    )

  ora_blocco = None
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
  if tipo_blocco == "Orario specifico":
    ora_blocco = st.selectbox(
        "Seleziona Orario da bloccare",
        TUTTI_GLI_ORARI_ADMIN,
        key="ora_blocco_input",
    )

  if st.button("Conferma Blocco Studio"):
    conn = sqlite3.connect("prenotazioni.db")
    c = conn.cursor()

    if tipo_blocco == "Tutta la giornata":
      for h in TUTTI_GLI_ORARI_ADMIN:
        c.execute(
            "SELECT id FROM prenotazioni WHERE data = ? AND ora = ?",
            (str(data_blocco), h),
        )
        if not c.fetchone():
          c.execute(
              "INSERT INTO prenotazioni (nome, data, ora, trattamento,"
              " data_creazione) VALUES (?, ?, ?, ?, ?)",
              (
                  "🔒 STUDIO CHIUSO",
                  str(data_blocco),
                  h,
                  "Chiusura Admin",
                  datetime.now().strftime("%Y-%m-%d %H:%M"),
              ),
          )
      st.success(
          f"Intera giornata del {data_blocco.strftime('%d/%m/%Y')}"
          " bloccata/chiusa con successo!"
      )
    else:
      c.execute(
          "SELECT id FROM prenotazioni WHERE data = ? AND ora = ?",
          (str(data_blocco), ora_blocco),
      )
      if c.fetchone():
        st.warning("Questo orario risulta già occupato o bloccato.")
      else:
        c.execute(
            "INSERT INTO prenotazioni (nome, data, ora, trattamento,"
            " data_creazione) VALUES (?, ?, ?, ?, ?)",
            (
                "🔒 ORARIO CHIUSO",
                str(data_blocco),
                ora_blocco,
                "Chiusura Admin",
                datetime.now().strftime("%Y-%m-%d %H:%M"),
            ),
        )
        st.success(
            f"Orario {ora_blocco} del {data_blocco.strftime('%d/%m/%Y')}"
            " bloccato con successo!"
        )

    conn.commit()
    conn.close()
    st.rerun()

  # SEZIONE SBLOCCO SPECULARE AL BLOCCO
  st.markdown("---")
  st.subheader("🔓 Gestione Sblocchi Studio")
  st.write(
      "Seleziona una data per sbloccare l'intera giornata o un singolo orario."
  )

  col_s1, col_s2 = st.columns(2)
  with col_s1:
    data_sblocco = st.date_input(
        "Data da sbloccare",
        min_value=datetime.today(),
        key="data_sblocco_input",
    )
  with col_s2:
    tipo_sblocco = st.radio(
        "Tipo di sblocco",
        ["Tutta la giornata", "Orario specifico"],
        key="tipo_sblocco_input",
    )

  ora_sblocco = None
  if tipo_sblocco == "Orario specifico":
    conn = sqlite3.connect("prenotazioni.db")
    c = conn.cursor()
    c.execute(
        "SELECT ora, nome FROM prenotazioni WHERE data = ?",
        (str(data_sblocco),),
    )
    slot_occupati = c.fetchall()
    conn.close()

    orari_occupati_data = [row[0] for row in slot_occupati]
    if orari_occupati_data:
      ora_sblocco = st.selectbox(
          "Seleziona Orario da sbloccare",
          orari_occupati_data,
          key="ora_sblocco_input",
      )
    else:
      st.info("Nessun orario occupato o bloccato in questa data.")

  if st.button("Conferma Sblocco Studio"):
    conn = sqlite3.connect("prenotazioni.db")
    c = conn.cursor()

    if tipo_sblocco == "Tutta la giornata":
      c.execute("DELETE FROM prenotazioni WHERE data = ?", (str(data_sblocco),))
      st.success(
          f"Tutti gli impegni e chiusure del"
          f" {data_sblocco.strftime('%d/%m/%Y')} sono stati rimossi e"
          " sbloccati!"
      )
    else:
      if ora_sblocco:
        c.execute(
            "DELETE FROM prenotazioni WHERE data = ? AND ora = ?",
            (str(data_sblocco), ora_sblocco),
        )
        st.success(
            f"Orario {ora_sblocco} del {data_sblocco.strftime('%d/%m/%Y')}"
            " sbloccato con successo!"
        )
      else:
        st.warning("Nessun orario valido selezionato da sbloccare.")

    conn.commit()
    conn.close()
    st.rerun()


# --- VISTA 2: PAGINA PRINCIPALE CLIENTE ---
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

    # RIQUADRO ROSA NATIVO
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

      # Calcolo orari già occupati o bloccati per la data selezionata
      conn = sqlite3.connect("prenotazioni.db")
      c = conn.cursor()
      c.execute(
          "SELECT ora FROM prenotazioni WHERE data = ?", (str(data_scelta),)
      )
      orari_occupati = [row[0] for row in c.fetchall()]
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
      orari_disponibili = [
          h for h in TUTTI_GLI_ORARI if h not in orari_occupati
      ]

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

      submitted = st.button("Conferma Prenotazione", type="primary")

    # Logica di salvataggio
    if submitted:
      if not nome.strip():
        st.error("Per favore inserisci il tuo nome e cognome.")
      elif not ora_scelta or ora_scelta == "Tutto occupato":
        st.error("Spiacenti, tutti gli orari per questa data sono già occupati.")
      else:
        # Controllo sicurezza finale sovrapposizione
        conn = sqlite3.connect("prenotazioni.db")
        c = conn.cursor()
        c.execute(
            "SELECT id FROM prenotazioni WHERE data = ? AND ora = ?",
            (str(data_scelta), ora_scelta),
        )
        gia_prenotato = c.fetchone()

        if gia_prenotato:
          st.error(
              "⚠️ Spiacenti, questo orario è stato appena occupato! Riprova con"
              " un altro orario."
          )
          conn.close()
        else:
          c.execute(
              "INSERT INTO prenotazioni (nome, data, ora, trattamento,"
              " data_creazione) VALUES (?, ?, ?, ?, ?)",
              (
                  nome,
                  str(data_scelta),
                  ora_scelta,
                  trattamento,
                  datetime.now().strftime("%Y-%m-%d %H:%M"),
              ),
          )
          conn.commit()
          conn.close()

          # Formattazione data italiana (es. 29/07/2026)
          data_formattata = data_scelta.strftime("%d/%m/%Y")

          # Messaggio di successo e attivazione flag per pulire solo il nome
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
