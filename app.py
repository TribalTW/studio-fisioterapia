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

# Personalizzazione Stile CSS
st.markdown(
    """
    <style>
    /* Riquadro rosa per il modulo di prenotazione */
    [data-testid="stForm"] {
        background-color: #FCE4EC;
        padding: 25px;
        border-radius: 16px;
        border: 1px solid #F8BBD0;
    }
    
    /* Campi di testo, selezioni e selettore data con sfondo bianco */
    .stTextInput input, .stSelectbox > div > div, .stDateInput input {
        background-color: #FFFFFF !important;
        border-radius: 8px !important;
        border: 1px solid #E0E0E0 !important;
    }
    
    /* Pulsante di conferma rosa magenta */
    div[data-testid="stFormSubmitButton"] > button {
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
    
    div[data-testid="stFormSubmitButton"] > button:hover {
        background-color: #C2185B !important;
    }
    
    /* Titoli in rosa scuro */
    h1, h2, h3 {
        color: #880E4F !important;
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

# --- BARRA LATERALE (Logo & Admin) ---
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

if logo_path:
  st.sidebar.image(logo_path, use_container_width=True)
else:
  st.sidebar.title("🧘‍♀️ Postura & Pilates")
  st.sidebar.caption("Dott.ssa Roberta Sinagra")

st.sidebar.markdown("---")
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

    st.markdown("---")
    st.subheader("🗑️ Elimina / Annulla Prenotazione")
    id_da_eliminare = st.number_input(
        "Inserisci l'ID della prenotazione da cancellare:", min_value=1, step=1
    )
    if st.button("Elimina Prenotazione"):
      conn = sqlite3.connect("prenotazioni.db")
      c = conn.cursor()
      c.execute("DELETE FROM prenotazioni WHERE id = ?", (id_da_eliminare,))
      conn.commit()
      conn.close()
      st.success(
          f"Prenotazione ID {id_da_eliminare} eliminata! L'orario è di nuovo"
          " libero."
      )
      st.rerun()
  else:
    st.info("Nessuna prenotazione presente nel database.")


# --- VISTA 2: PAGINA PRINCIPALE CLIENTE ---
else:
  st.title("Postura & Pilates")
  st.subheader("Dott.ssa Roberta Sinagra")

  # Schede di Navigazione
  tab1, tab2, tab3, tab4 = st.tabs([
      "📅 Prenota",
      "ℹ️ Info Studio",
      "📍 Dove Siamo",
      "📜 Regolamento",
  ])

  # TAB 1: PRENOTAZIONE DINAMICA
  with tab1:
    st.markdown("### Modulo di Prenotazione")

    # 1. Seleziona la data PRIMA del modulo per calcolare gli orari liberi
    data_scelta = st.date_input(
        "Seleziona Data desiderata *", min_value=datetime.today()
    )

    # Controlla quali orari sono GIA' prenotati per questa data nel Database
    conn = sqlite3.connect("prenotazioni.db")
    c = conn.cursor()
    c.execute(
        "SELECT ora FROM prenotazioni WHERE data = ?", (str(data_scelta),)
    )
    orari_occupati = [row[0] for row in c.fetchall()]
    conn.close()

    # Tutti gli orari di lavoro possibili dello studio
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

    # Mostra SOLO gli orari non ancora occupati
    orari_disponibili = [h for h in TUTTI_GLI_ORARI if h not in orari_occupati]

    # Se la giornata è piena, blocca le prenotazioni per quel giorno
    if not orari_disponibili:
      st.warning(
          "⚠️ Spiacenti, tutti gli orari per questa data sono già stati"
          " prenotati. Per favore seleziona un'altra data!"
      )
    else:
      with st.form("booking_form"):
        nome = st.text_input("Nome e Cognome *")
        trattamento = st.selectbox(
            "Seleziona Trattamento / Lezione *",
            [
                "Valutazione Posturale",
                "Lezione Pilates Individuale",
                "Pilates Duetto (in coppia)",
                "Rieducazione Posturale Motorìa",
            ],
        )

        ora_scelta = st.selectbox(
            "Seleziona Ora Disponibile *", orari_disponibili
        )

        submitted = st.form_submit_button("Conferma Prenotazione")

        if submitted:
          if nome.strip() == "":
            st.error("Per favore inserisci il tuo nome e cognome.")
          else:
            # Controllo di sicurezza finale prima di inserire
            conn = sqlite3.connect("prenotazioni.db")
            c = conn.cursor()
            c.execute(
                "SELECT id FROM prenotazioni WHERE data = ? AND ora = ?",
                (str(data_scelta), ora_scelta),
            )
            gia_prenotato = c.fetchone()

            if gia_prenotato:
              st.error(
                  "⚠️ Spiacenti, questo orario è stato appena occupato!"
                  " Riprova con un altro orario."
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
              st.success(
                  f"✨ Prenotazione confermata per {nome} il {data_scelta} alle"
                  f" {ora_scelta}!"
              )
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
