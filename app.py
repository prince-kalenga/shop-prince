# app.py
"""
Application Web de Gestion de Shop PRINCE
Framework: Streamlit
Base de données: SQLite3
"""

import streamlit as st
import pandas as pd
import datetime
import sqlite3
import os

# ---------------------------------------------------------
# CONFIGURATION & BASE DE DONNÉES
# ---------------------------------------------------------
st.set_page_config(
    page_title="Shop PRINCE - Gestion Web",
    page_icon="📱",
    layout="wide"
)

DB_PATH = "shop_prince.db"

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS days (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT UNIQUE,
            own_capital REAL,
            initial_debt REAL,
            new_debts REAL,
            repayments REAL,
            capital_additions REAL,
            shop_expenses REAL,
            cash REAL,
            airtel_money REAL,
            mpesa REAL,
            orange_money REAL,
            observation TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            day_id INTEGER,
            network_name TEXT,
            stock_initial REAL,
            units_in REAL,
            unit_buy_price REAL,
            unit_sell_price REAL,
            stock_final REAL,
            FOREIGN KEY (day_id) REFERENCES days (id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            type TEXT,
            source_target TEXT,
            amount REAL,
            note TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS debts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            type TEXT,
            amount REAL,
            note TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value REAL
        )
    """)

    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('pct_savings', 50.0)")
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('pct_reinvest', 25.0)")
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('pct_allowance', 25.0)")

    conn.commit()
    conn.close()

init_db()

# ---------------------------------------------------------
# FONCTIONS DE CALCUL
# ---------------------------------------------------------
def calc_network(s_init, u_in, p_buy, p_sell, s_final):
    total_u = s_init + u_in
    sold = total_u - s_final
    rev = sold * p_sell
    cost = sold * p_buy
    profit = rev - cost
    return {'units_sold': sold, 'revenue': rev, 'cost': cost, 'profit': profit, 'stock_buy_val': s_final * p_buy}

# ---------------------------------------------------------
# BARRE LATÉRALE / NAVIGATION
# ---------------------------------------------------------
st.sidebar.title("SHOP PRINCE 📱")
st.sidebar.caption("Gestion de Shop Mobile Money & Recharge")

menu = st.sidebar.radio(
    "Navigation", 
    ["🏠 Tableau de bord", "📦 Inventaire", "💰 Transactions", "💳 Dettes", "📊 Historique & Export", "⚙️ Paramètres"]
)

# ---------------------------------------------------------
# 1. TABLEAU DE BORD
# ---------------------------------------------------------
if menu == "🏠 Tableau de bord":
    st.header("Tableau de Bord - Synthèse du Capital")

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM days ORDER BY date DESC LIMIT 1")
    last_day = cursor.fetchone()

    if not last_day:
        st.info("Aucune donnée enregistrée pour le moment. Allez dans la section 'Inventaire' pour débuter.")
    else:
        cursor.execute("SELECT * FROM inventory WHERE day_id = ?", (last_day['id'],))
        invs = cursor.fetchall()

        tot_rev, tot_cost, tot_profit, tot_stock_buy = 0, 0, 0, 0
        net_rows = []

        for inv in invs:
            res = calc_network(inv['stock_initial'], inv['units_in'], inv['unit_buy_price'], inv['unit_sell_price'], inv['stock_final'])
            tot_rev += res['revenue']
            tot_cost += res['cost']
            tot_profit += res['profit']
            tot_stock_buy += res['stock_buy_val']
            net_rows.append({
                "Réseau": inv['network_name'],
                "Vendu": f"{res['units_sold']:,.0f}",
                "Recettes (FC)": f"{res['revenue']:,.0f}",
                "Coût Achat (FC)": f"{res['cost']:,.0f}",
                "Bénéfice (FC)": f"{res['profit']:,.0f}",
                "Stock Restant": f"{inv['stock_final']:,.0f}"
            })

        cash_avail = last_day['cash'] + last_day['airtel_money'] + last_day['mpesa'] + last_day['orange_money']
        debt_status = (last_day['initial_debt'] + last_day['new_debts']) - last_day['repayments']
        total_capital = tot_stock_buy + tot_rev + cash_avail
        net_sit = (cash_avail + tot_stock_buy) - debt_status

        # Cartes métriques
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Recettes du jour (brutes)", f"{tot_rev:,.0f} FC")
        c2.metric("Disponible Caisse/SIMs", f"{cash_avail:,.0f} FC")
        c3.metric("Valeur Stock Restant", f"{tot_stock_buy:,.0f} FC")
        c4.metric("Bénéfice Brut", f"{tot_profit:,.0f} FC")

        c5, c6, c7, c8 = st.columns(4)
        c5.metric("Total Capital Roulement", f"{total_capital:,.0f} FC")
        c6.metric("Dette Restante", f"{debt_status:,.0f} FC")
        c7.metric("Situation Nette", f"{net_sit:,.0f} FC")
        c8.metric("Dépenses Shop", f"{last_day['shop_expenses']:,.0f} FC")

        st.caption("💡 *Total Capital de Roulement = Stock restant (prix d'achat) + Recettes brutes + Argent Caisse/SIMs*")

        st.subheader("Bilan par Réseau")
        st.dataframe(pd.DataFrame(net_rows), use_container_width=True)

    conn.close()

# ---------------------------------------------------------
# 2. INVENTAIRE (CRÉATION ET MODIFICATION)
# ---------------------------------------------------------
elif menu == "📦 Inventaire":
    st.header("Saisie & Modification d'un Inventaire")

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT date FROM days ORDER BY date DESC")
    dates_list = [row['date'] for row in cursor.fetchall()]

    mode = st.radio("Mode de saisie :", ["Nouvel inventaire", "Modifier un inventaire existant"], horizontal=True)

    selected_date = datetime.date.today()
    day_data = None

    if mode == "Modifier un inventaire existant":
        if dates_list:
            target_date_str = st.selectbox("Sélectionner la date à modifier :", dates_list)
            cursor.execute("SELECT * FROM days WHERE date = ?", (target_date_str,))
            day_data = cursor.fetchone()
            selected_date = datetime.datetime.strptime(day_data['date'], "%Y-%m-%d").date()
        else:
            st.warning("Aucun inventaire disponible pour modification.")

    with st.form("inventory_form"):
        st.subheader("1. Informations Générales")
        col_date, col_cap, col_expenses = st.columns(3)
        inv_date = col_date.date_input("Date", selected_date)
        own_cap = col_cap.number_input("Capital Propre Int.", value=float(day_data['own_capital']) if day_data else 0.0)
        expenses = col_expenses.number_input("Dépenses Shop", value=float(day_data['shop_expenses']) if day_data else 0.0)

        col_d1, col_d2, col_d3 = st.columns(3)
        init_debt = col_d1.number_input("Dette Initiale", value=float(day_data['initial_debt']) if day_data else 0.0)
        new_debts = col_d2.number_input("Nouvelles Dettes", value=float(day_data['new_debts']) if day_data else 0.0)
        repayments = col_d3.number_input("Remboursements", value=float(day_data['repayments']) if day_data else 0.0)

        obs = st.text_input("Observation / Notes", value=day_data['observation'] if day_data and day_data['observation'] else "")

        st.subheader("2. Stocks & Ventes par Réseau")
        net_inputs = {}
        for net_name in ["Airtel", "Vodacom", "Orange"]:
            st.markdown(f"**Réseau {net_name}**")
            
            # Récupérer données existantes
            inv_net = None
            if day_data:
                cursor.execute("SELECT * FROM inventory WHERE day_id = ? AND network_name = ?", (day_data['id'], net_name))
                inv_net = cursor.fetchone()

            c1, c2, c3, c4, c5 = st.columns(5)
            s_init = c1.number_input(f"Stock Init ({net_name})", value=float(inv_net['stock_initial']) if inv_net else 0.0)
            u_in = c2.number_input(f"Entrées ({net_name})", value=float(inv_net['units_in']) if inv_net else 0.0)
            p_buy = c3.number_input(f"Prix Achat U. ({net_name})", value=float(inv_net['unit_buy_price']) if inv_net else 0.0)
            p_sell = c4.number_input(f"Prix Vente U. ({net_name})", value=float(inv_net['unit_sell_price']) if inv_net else 0.0)
            s_final = c5.number_input(f"Stock Restant ({net_name})", value=float(inv_net['stock_final']) if inv_net else 0.0)

            net_inputs[net_name] = (s_init, u_in, p_buy, p_sell, s_final)

        st.subheader("3. Argent disponible en fin de journée")
        c_cash, c_airtel, c_mpesa, c_orange = st.columns(4)
        cash = c_cash.number_input("Espèces (Caisse)", value=float(day_data['cash']) if day_data else 0.0)
        airtel_m = c_airtel.number_input("Airtel Money", value=float(day_data['airtel_money']) if day_data else 0.0)
        mpesa = c_mpesa.number_input("M-Pesa", value=float(day_data['mpesa']) if day_data else 0.0)
        orange_m = c_orange.number_input("Orange Money", value=float(day_data['orange_money']) if day_data else 0.0)

        submit = st.form_submit_button("💾 Enregistrer l'inventaire")

        if submit:
            date_str = str(inv_date)
            cursor.execute("INSERT OR REPLACE INTO days (id, date, own_capital, initial_debt, new_debts, repayments, capital_additions, shop_expenses, cash, airtel_money, mpesa, orange_money, observation) VALUES ((SELECT id FROM days WHERE date = ?), ?, ?, ?, ?, ?, 0, ?, ?, ?, ?, ?, ?)", 
                           (date_str, date_str, own_cap, init_debt, new_debts, repayments, expenses, cash, airtel_m, mpesa, orange_m, obs))
            
            cursor.execute("SELECT id FROM days WHERE date = ?", (date_str,))
            day_id = cursor.fetchone()['id']

            cursor.execute("DELETE FROM inventory WHERE day_id = ?", (day_id,))

            for net_name, vals in net_inputs.items():
                cursor.execute("""
                    INSERT INTO inventory (day_id, network_name, stock_initial, units_in, unit_buy_price, unit_sell_price, stock_final)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (day_id, net_name, vals[0], vals[1], vals[2], vals[3], vals[4]))

            conn.commit()
            st.success(f"Inventaire enregistré pour le {date_str} !")
            st.rerun()

    conn.close()

# ---------------------------------------------------------
# 3. TRANSACTIONS
# ---------------------------------------------------------
elif menu == "💰 Transactions":
    st.header("Gestion des Transactions Financières")

    with st.form("trans_form"):
        col1, col2, col3, col4 = st.columns(4)
        t_date = col1.date_input("Date", datetime.date.today())
        t_type = col2.selectbox("Type", ["Dépôt", "Retrait", "Dépense", "Apport de capital"])
        t_target = col3.selectbox("Compte", ["Cash", "Airtel Money", "M-Pesa", "Orange Money"])
        t_amount = col4.number_input("Montant (FC)", min_value=0.0)
        t_note = st.text_input("Note / Détail")

        if st.form_submit_button("➕ Ajouter la transaction"):
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("INSERT INTO transactions (date, type, source_target, amount, note) VALUES (?, ?, ?, ?, ?)", 
                           (str(t_date), t_type, t_target, t_amount, t_note))
            conn.commit()
            conn.close()
            st.success("Transaction ajoutée !")
            st.rerun()

    st.subheader("Historique des Transactions")
    conn = get_connection()
    df_trans = pd.read_sql_query("SELECT id, date, type, source_target AS Compte, amount AS 'Montant (FC)', note AS Note FROM transactions ORDER BY id DESC", conn)
    conn.close()
    st.dataframe(df_trans, use_container_width=True)

# ---------------------------------------------------------
# 4. DETTES (AVEC MODIFICATION)
# ---------------------------------------------------------
elif menu == "💳 Dettes":
    st.header("Gestion des Dettes & Remboursements")

    conn = get_connection()
    df_debts = pd.read_sql_query("SELECT id, date, type, amount AS 'Montant (FC)', note AS Note FROM debts ORDER BY id DESC", conn)
    conn.close()

    col_form, col_table = st.columns([1, 2])

    with col_form:
        st.subheader("Saisie / Modification")
        
        debt_id_to_edit = st.number_input("ID à modifier (0 pour nouvelle entrée)", min_value=0, step=1, value=0)
        
        debt_row = None
        if debt_id_to_edit > 0 and not df_debts.empty:
            match = df_debts[df_debts['id'] == debt_id_to_edit]
            if not match.empty:
                debt_row = match.iloc[0]

        with st.form("debt_form"):
            d_date = st.date_input("Date", datetime.datetime.strptime(debt_row['date'], "%Y-%m-%d").date() if debt_row else datetime.date.today())
            d_type = st.selectbox("Type", ["Nouvelle dette", "Remboursement"], index=0 if not debt_row or debt_row['type'] == "Nouvelle dette" else 1)
            d_amount = st.number_input("Montant (FC)", value=float(debt_row['Montant (FC)']) if debt_row else 0.0)
            d_note = st.text_input("Note", value=debt_row['Note'] if debt_row and debt_row['Note'] else "")

            submit_debt = st.form_submit_button("💾 Enregistrer")

            if submit_debt:
                conn = get_connection()
                cursor = conn.cursor()
                if debt_id_to_edit > 0:
                    cursor.execute("UPDATE debts SET date = ?, type = ?, amount = ?, note = ? WHERE id = ?", 
                                   (str(d_date), d_type, d_amount, d_note, debt_id_to_edit))
                    st.success("Dette mise à jour !")
                else:
                    cursor.execute("INSERT INTO debts (date, type, amount, note) VALUES (?, ?, ?, ?)", 
                                   (str(d_date), d_type, d_amount, d_note))
                    st.success("Dette enregistrée !")
                conn.commit()
                conn.close()
                st.rerun()

    with col_table:
        st.subheader("Historique des Dettes")
        st.dataframe(df_debts, use_container_width=True)

# ---------------------------------------------------------
# 5. HISTORIQUE & EXPORT
# ---------------------------------------------------------
elif menu == "📊 Historique & Export":
    st.header("Historique Global & Graphiques")

    conn = get_connection()
    df_days = pd.read_sql_query("SELECT * FROM days ORDER BY date ASC", conn)
    conn.close()

    if not df_days.empty:
        st.subheader("Graphique d'évolution des ventes")
        st.line_chart(df_days.set_index("date")[["cash", "own_capital", "shop_expenses"]])

        st.subheader("Données consolidées")
        st.dataframe(df_days, use_container_width=True)

        # Export Excel
        csv_data = df_days.to_csv(index=False).encode('utf-8')
        st.download_button("📝 Télécharger l'historique en CSV", csv_data, "historique_shop.csv", "text/csv")

# ---------------------------------------------------------
# 6. PARAMÈTRES
# ---------------------------------------------------------
elif menu == "⚙️ Paramètres":
    st.header("Paramètres de Répartition")

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM settings")
    settings = {row['key']: row['value'] for row in cursor.fetchall()}

    with st.form("settings_form"):
        s = st.number_input("Épargne (%)", value=float(settings.get('pct_savings', 50.0)))
        r = st.number_input("Réinvestissement (%)", value=float(settings.get('pct_reinvest', 25.0)))
        a = st.number_input("Argent de poche (%)", value=float(settings.get('pct_allowance', 25.0)))

        if st.form_submit_button("Enregistrer"):
            if abs((s + r + a) - 100.0) > 0.001:
                st.error("La somme des pourcentages doit être égale à 100%.")
            else:
                cursor.execute("UPDATE settings SET value = ? WHERE key = 'pct_savings'", (s,))
                cursor.execute("UPDATE settings SET value = ? WHERE key = 'pct_reinvest'", (r,))
                cursor.execute("UPDATE settings SET value = ? WHERE key = 'pct_allowance'", (a,))
                conn.commit()
                st.success("Paramètres sauvegardés !")
    conn.close()
