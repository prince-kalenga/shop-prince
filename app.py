# app.py
import streamlit as st
import pandas as pd
import datetime
import sqlite3

# Configuration de la page
st.set_page_config(page_title="Shop PRINCE - Web", layout="wide", page_icon="📱")

# Connexion DB (SQLite local pour test, ou PostgreSQL/Supabase en ligne)
def get_connection():
    conn = sqlite3.connect("shop_prince.db")
    conn.row_factory = sqlite3.Row
    return conn

# Menu de Navigation
st.sidebar.title("SHOP PRINCE 📱")
menu = st.sidebar.radio("Navigation", [
    "🏠 Tableau de bord", 
    "📦 Inventaire", 
    "💰 Transactions", 
    "💳 Dettes", 
    "📊 Historique"
])

# ---------------------------------------------------------
# 1. TABLEAU DE BORD
# ---------------------------------------------------------
if menu == "🏠 Tableau de bord":
    st.header("Tableau de Bord - Synthèse du Capital")
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Recettes du jour", "150,000 FC")
    col2.metric("Disponible Caisse/SIMs", "450,000 FC")
    col3.metric("Valeur Stock (Achat)", "1,200,000 FC")
    col4.metric("Bénéfice Net", "35,000 FC", delta="5,000 FC")

# ---------------------------------------------------------
# 2. SAISIE DE L'INVENTAIRE
# ---------------------------------------------------------
elif menu == "📦 Inventaire":
    st.header("Enregistrer un Inventaire Journalier")
    
    with st.form("inventory_form"):
        date_inv = st.date_input("Date", datetime.date.today())
        
        st.subheader("Détails des Réseaux")
        col_airtel, col_voda, col_orange = st.columns(3)
        
        with col_airtel:
            st.markdown("**Airtel**")
            airtel_init = st.number_input("Stock Init. Airtel", value=0)
            airtel_final = st.number_input("Stock Final Airtel", value=0)
            
        with col_voda:
            st.markdown("**Vodacom**")
            voda_init = st.number_input("Stock Init. Vodacom", value=0)
            voda_final = st.number_input("Stock Final Vodacom", value=0)

        with col_orange:
            st.markdown("**Orange**")
            orange_init = st.number_input("Stock Init. Orange", value=0)
            orange_final = st.number_input("Stock Final Orange", value=0)

        submitted = st.form_submit_button("💾 Enregistrer l'inventaire")
        if submitted:
            st.success(f"Inventaire enregistré pour le {date_inv} !")

# ---------------------------------------------------------
# 3. GESTION DES DETTES (Avec Modification)
# ---------------------------------------------------------
elif menu == "💳 Dettes":
    st.header("Gestion des Dettes & Remboursements")
    
    col_form, col_table = st.columns([1, 2])
    
    with col_form:
        st.subheader("Saisie / Modification")
        d_date = st.date_input("Date dette", datetime.date.today())
        d_type = st.selectbox("Type", ["Nouvelle dette", "Remboursement"])
        d_amount = st.number_input("Montant (FC)", min_value=0)
        d_note = st.text_input("Note / Libellé")
        
        if st.button("➕ Enregistrer / Mettre à jour"):
            st.success("Mouvement de dette enregistré !")

    with col_table:
        st.subheader("Historique des dettes")
        # Exemple de données affichées dans un tableau interactif
        data_debts = pd.DataFrame([
            {"ID": 1, "Date": "2026-09-24", "Type": "Nouvelle dette", "Montant (FC)": 50000, "Note": "Fournisseur A"},
            {"ID": 2, "Date": "2026-09-24", "Type": "Remboursement", "Montant (FC)": 20000, "Note": "Acompte"}
        ])
        st.dataframe(data_debts, use_container_width=True)

# ---------------------------------------------------------
# 4. HISTORIQUE & GRAPHIQUES
# ---------------------------------------------------------
elif menu == "📊 Historique":
    st.header("Historique des Ventes & Graphiques")
    
    # Données de démonstration
    chart_data = pd.DataFrame({
        'Date': pd.date_range(start='2026-09-01', periods=10),
        'Recettes (FC)': [100000, 120000, 90000, 150000, 130000, 170000, 160000, 140000, 180000, 200000],
        'Bénéfice (FC)': [15000, 18000, 12000, 22000, 19000, 25000, 23000, 20000, 27000, 30000]
    }).set_index('Date')

    st.bar_chart(chart_data)