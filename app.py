with st.form("form_checkin_cliente_automatico"):
                            nome_inserito = st.text_input("Inserisci il tuo Nome e Cognome *")
                            submit_checkin = st.form_submit_button("✅ Conferma la mia Presenza")

                            if submit_checkin:
                                nome_pulito = nome_inserito.strip()

                                if not nome_pulito:
                                    st.error("Per favore, inserisci il tuo nome e cognome.")
                                else:
                                    # CONTROLLO SICURO MA TRASPARENTE: Nome esatto + Stesso Smartphone (device_id)
                                    conn = sqlite3.connect("prenotazioni.db")
                                    c = conn.cursor()
                                    c.execute(
                                        """
                                        SELECT id, nome, trattamento, ora, stato_presenza 
                                        FROM prenotazioni 
                                        WHERE data = ? 
                                          AND device_id != 'SYSTEM' 
                                          AND LOWER(nome) = ? 
                                          AND device_id = ?
                                        """,
                                        (oggi_str, nome_pulito.lower(), client_device_id),
                                    )
                                    appuntamenti_trovati = c.fetchall()
                                    conn.close()

                                    if not appuntamenti_trovati:
                                        st.error(
                                            "❌ Non risultano prenotazioni a questo nome effettuate da questo dispositivo per la giornata odierna."
                                        )
                                    else:
                                        # (Segue il controllo della fascia oraria di 45 min prima / 30 min dopo...)
