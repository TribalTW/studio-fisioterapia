import sqlite3
import pandas as pd
import streamlit as st
from datetime import date

# Configurazione pagina mobile-friendly
st.set_page_config(
    page_title="Studio Fisioterapia", page_icon="🩺", layout="centered"
)

# 🔑 IMPOSTA QUI LA TUA PASSWORD ADMIN
ADMIN_PASSWORD = "fisiostudio2026"

# Connessione / Creazione Database SQLite
conn = sqlite3.connect("prenotazioni.db", check_same_thread=False)
c = conn.cursor()
c.execute("""
    CREATE TABLE IF NOT EXISTS appuntamenti (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT,
        telefono TEXT,
        servizio TEXT,
        data TEXT,
        ora TEXT
    )
""")
conn.commit()

# Menu di navigazione nella barra laterale
st.sidebar.title("📌 Menu")
scelta = st.sidebar.radio(
    "Seleziona Pagina:", ["Prenota Appuntamento", "Area Riservata (Admin)"]
)

# =========================================================
# 1. INTERFACCIA CLIENTI (PRENOTAZIONE)
# =========================================================
if scelta == "Prenota Appuntamento":
  st.title("🩺 Studio Fisioterapia")
  st.subheader("Prenota la tua seduta da casa")

  with st.form("form_prenotazione"):
    nome = st.text_input("Nome e Cognome *")
    telefono = st.text_input("Numero di Telefono *")
    servizio = st.selectbox(
        "Tipo di Trattamento",
        [
            "Prima Visita + Valutazione",
            "Seduta di Riabilitazione",
            "Massoterapia / Terapia Manuale",
            "Tecarterapia",
        ],
    )

    col1, col2 = st.columns(2)
    with col1:
      data_pren = st.date_input("Data", min_value=date.today())
    with col2:
      ora_pren = st.selectbox(
          "Orario",
          ["09:00", "10:00", "11:00", "14:30", "15:30", "16:30", "17:30"],
      )

    submitted = st.form_submit_button("Conferma Prenotazione")

    if submitted:
      if not nome or not telefono:
        st.error("Per favore compila tutti i campi obbligatori.")
      else:
        # Verifica se l'orario è già occupato
        c.execute(
            "SELECT * FROM appuntamenti WHERE data=? AND ora=?",
            (str(data_pren), ora_pren),
        )
        if c.fetchone():
          st.warning(
              "Ci dispiace, questo orario è già stato prenotato. Scegli un altro"
              " orario."
          )
        else:
          c.execute(
              "INSERT INTO appuntamenti (nome, telefono, servizio, data, ora)"
              " VALUES (?, ?, ?, ?, ?)",
              (nome, telefono, servizio, str(data_pren), ora_pren),
          )
          conn.commit()
          st.success(
              f"Prenotazione confermata per il {data_pren} alle {ora_pren}!"
          )

# =========================================================
# 2. AREA RISERVATA ADMIN (GESTIONE & CANCELLAZIONE)
# =========================================================
elif scelta == "Area Riservata (Admin)":
  st.title("🔒 Area Riservata Fisioterapista")

  password_inserita = st.text_input(
      "Inserisci la password di amministrazione", type="password"
  )

  if password_inserita == ADMIN_PASSWORD:
    st.success("Accesso eseguito!")
    st.divider()

    # Visualizzazione Prenotazioni
    st.subheader("📋 Appuntamenti Registrati")

    df = pd.read_sql_query(
        "SELECT id, nome, telefono, servizio, data, ora FROM appuntamenti"
        " ORDER BY data ASC, ora ASC",
        conn,
    )

    if df.empty:
      st.info("Non ci sono appuntamenti in archivio.")
    else:
      # Mostra la tabella su schermo
      st.dataframe(df, use_container_width=True)

      # Tasto per esportare la lista in formato CSV (apribile con Excel)
      csv = df.to_csv(index=False).encode("utf-8")
      st.download_button(
          label="📥 Scarica Lista (Excel/CSV)",
          data=csv,
          file_name="appuntamenti_studio.csv",
          mime="text/csv",
      )

      st.divider()

      # Sezione di Cancellazione
      st.subheader("❌ Annulla una Prenotazione")

      # Crea un menu a tendina formattato con i dettagli di ogni prenotazione
      lista_opzioni = {
          f"ID {row['id']} | {row['nome']} - {row['data']} ore {row['ora']}"
          f" ({row['servizio']})": row["id"]
          for _, row in df.iterrows()
      }

      selezione = st.selectbox(
          "Seleziona l'appuntamento da cancellare:",
          options=list(lista_opzioni.keys()),
      )

      if st.button("Elimina Definitivamente", type="primary"):
        id_da_eliminare = lista_opzioni[selezione]
        c.execute("DELETE FROM appuntamenti WHERE id=?", (id_da_eliminare,))
        conn.commit()
        st.success("Appuntamento eliminato con successo!")
        st.rerun()  # Ricarica l'app per aggiornare subito la lista visualizzata

  elif password_inserita != "":
    st.error("Password errata. Riprova.")