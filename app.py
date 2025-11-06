import streamlit as st
import pandas as pd
import psycopg2
import matplotlib.pyplot as plt
import seaborn as sns

# ===============================
# CONFIGURARE BAZĂ DE DATE
# ===============================
DB_CONFIG = {
    "host": "localhost",
    "dbname": "muzica",
    "user": "postgres",
    "password": "123"
}

@st.cache_data
def run_query(query):
    conn = psycopg2.connect(**DB_CONFIG)
    df = pd.read_sql(query, conn)
    conn.close()
    df.columns = [c.lower() for c in df.columns]  # conversie nume coloane la litere mici
    return df


# ===============================
# INTERFAȚĂ PRINCIPALĂ
# ===============================
st.set_page_config(page_title="Dashboard Vânzări Muzicale", layout="wide")
st.title("🎶 Dashboard Analiză Vânzări Muzicale")

menu = st.sidebar.selectbox(
    "Alege secțiunea:",
    [
        "1️⃣ Asocieri vânzări-genuri",
        "2️⃣ Evoluția vânzărilor pe luni",
        "3️⃣ Necesar aprovizionare",
        "4️⃣ Vânzări în perioada evenimentelor",
        "5️⃣ Impact promoții",
        "6️⃣ Top produse",
        "7️⃣ Vânzări medii pe client",
        "8️⃣ Clienți fideli",
        "9️⃣ Profitabilitate pe gen și oraș"
    ]
)

# ===============================
# 1️⃣ Asocieri vânzări-genuri
# ===============================
if menu == "1️⃣ Asocieri vânzări-genuri":
    st.subheader("Asocieri între vârstă, studii și genuri muzicale")

    query = """
    SELECT 
        CASE 
            WHEN EXTRACT(YEAR FROM AGE(CURRENT_DATE, c.DataNasterii)) BETWEEN 18 AND 24 THEN '18-24 ani'
            WHEN EXTRACT(YEAR FROM AGE(CURRENT_DATE, c.DataNasterii)) BETWEEN 25 AND 45 THEN '25-45 ani'
            WHEN EXTRACT(YEAR FROM AGE(CURRENT_DATE, c.DataNasterii)) BETWEEN 46 AND 65 THEN '46-65 ani'
            ELSE '65+ ani'
        END AS grupvarsta,
        c.NivelStudii,
        cat.Nume AS genmuzical,
        SUM(d.TotalLinie) AS totalvanzari
    FROM Client c
    JOIN Comanda co ON c.ClientID = co.ClientID
    JOIN DetaliuComanda d ON co.ComandaID = d.ComandaID
    JOIN Produs p ON d.ProdusID = p.ProdusID
    JOIN CategorieProdus cat ON p.CategorieProdusID = cat.CategorieProdusID
    GROUP BY grupvarsta, c.NivelStudii, cat.Nume
    ORDER BY grupvarsta, c.NivelStudii, totalvanzari DESC;
    """
    df = run_query(query)
    st.dataframe(df)

    if not df.empty:
        fig, ax = plt.subplots(figsize=(10, 5))
        sns.barplot(data=df, x="genmuzical", y="totalvanzari", hue="grupvarsta", ax=ax)
        plt.xticks(rotation=45)
        st.pyplot(fig)

# ===============================
# 2️⃣ Evoluția vânzărilor pe luni
# ===============================
elif menu == "2️⃣ Evoluția vânzărilor pe luni":
    st.subheader("Evoluția vânzărilor lunare pe genuri muzicale")

    query = """
    SELECT 
        DATE_TRUNC('month', co.DataComanda) AS luna,
        cat.Nume AS genmuzical,
        SUM(d.TotalLinie) AS totalvanzari
    FROM Comanda co
    JOIN DetaliuComanda d ON co.ComandaID = d.ComandaID
    JOIN Produs p ON d.ProdusID = p.ProdusID
    JOIN CategorieProdus cat ON p.CategorieProdusID = cat.CategorieProdusID
    GROUP BY luna, cat.Nume
    ORDER BY luna;
    """
    df = run_query(query)
    st.dataframe(df)

    if not df.empty:
        fig, ax = plt.subplots(figsize=(10, 5))
        sns.lineplot(data=df, x="luna", y="totalvanzari", hue="genmuzical", marker="o", ax=ax)
        plt.xticks(rotation=45)
        st.pyplot(fig)

# ===============================
# 3️⃣ Necesar aprovizionare
# ===============================
elif menu == "3️⃣ Necesar aprovizionare":
    st.subheader("Estimarea necesarului de aprovizionare pe suporturi (CD, DVD, Casetă)")

    query = """
    SELECT 
        p.TipSuport AS tipsuport,
        SUM(d.Cantitate) AS totalvandut,
        ROUND(AVG(d.Cantitate) * 1.2, 2) AS necesarestimativ
    FROM DetaliuComanda d
    JOIN Produs p ON d.ProdusID = p.ProdusID
    GROUP BY p.TipSuport;
    """
    df = run_query(query)
    st.dataframe(df)

    if not df.empty:
        fig, ax = plt.subplots(figsize=(7, 4))
        sns.barplot(data=df, x="tipsuport", y="necesarestimativ", ax=ax)
        st.pyplot(fig)

# ===============================
# 4️⃣ Vânzări în perioada evenimentelor
# ===============================
elif menu == "4️⃣ Vânzări în perioada evenimentelor":
    st.subheader("Evoluția vânzărilor în jurul evenimentelor externe")

    query = """
    SELECT 
        e.Nume AS eveniment,
        e.DataEveniment AS dataeveniment,
        SUM(d.TotalLinie) AS totalvanzari
    FROM Eveniment e
    JOIN Comanda co ON co.DataComanda BETWEEN e.DataEveniment - INTERVAL '3 days' AND e.DataEveniment + INTERVAL '3 days'
    JOIN DetaliuComanda d ON co.ComandaID = d.ComandaID
    GROUP BY e.Nume, e.DataEveniment
    ORDER BY e.DataEveniment;
    """
    df = run_query(query)
    st.dataframe(df)

    if not df.empty:
        fig, ax = plt.subplots(figsize=(10, 4))
        sns.barplot(data=df, x="eveniment", y="totalvanzari", ax=ax)
        plt.xticks(rotation=45)
        st.pyplot(fig)

# ===============================
# 5️⃣ Impact promoții
# ===============================
elif menu == "5️⃣ Impact promoții":
    st.subheader("Analiza impactului promoțiilor asupra vânzărilor estimate")

    query = """
    SELECT 
        p.Nume AS produs,
        cat.Nume AS genmuzical,
        pr.Reducere AS reducereprocent,
        SUM(d.Cantitate) AS cantitatevanduta,
        ROUND(SUM(d.TotalLinie), 2) AS totalvanzariactuale,
        ROUND(SUM(d.TotalLinie) * (1 + (pr.Reducere / 100.0) * 0.5), 2) AS totalvanzariestimate
    FROM DetaliuComanda d
    JOIN Produs p ON d.ProdusID = p.ProdusID
    JOIN CategorieProdus cat ON p.CategorieProdusID = cat.CategorieProdusID
    JOIN Promotie pr ON p.ProdusID = pr.ProdusID
    GROUP BY p.Nume, cat.Nume, pr.Reducere
    ORDER BY totalvanzariestimate DESC
    LIMIT 30;
    """
    df = run_query(query)
    st.dataframe(df)

    if not df.empty:
        fig, ax = plt.subplots(figsize=(10, 4))
        sns.scatterplot(data=df, x="reducereprocent", y="totalvanzariestimate", hue="genmuzical", s=100, ax=ax)
        st.pyplot(fig)

# ===============================
# 6️⃣ Top produse
# ===============================
elif menu == "6️⃣ Top produse":
    st.subheader("Top 10 produse cele mai vândute")

    query = """
    SELECT 
        p.Nume AS produs,
        cat.Nume AS genmuzical,
        SUM(d.Cantitate) AS totalvandut
    FROM DetaliuComanda d
    JOIN Produs p ON d.ProdusID = p.ProdusID
    JOIN CategorieProdus cat ON p.CategorieProdusID = cat.CategorieProdusID
    GROUP BY p.Nume, cat.Nume
    ORDER BY totalvandut DESC
    LIMIT 10;
    """
    df = run_query(query)
    st.dataframe(df)

    if not df.empty:
        fig, ax = plt.subplots(figsize=(10, 4))
        sns.barplot(data=df, x="produs", y="totalvandut", hue="genmuzical", ax=ax)
        plt.xticks(rotation=45)
        st.pyplot(fig)

# ===============================
# 7️⃣ Vânzări medii pe client
# ===============================
elif menu == "7️⃣ Vânzări medii pe client":
    st.subheader("Analiza valorii medii a comenzilor per client")

    query = """
    SELECT
        INITCAP(c.Prenume || ' ' || c.Nume) AS numeclient,
        COUNT(DISTINCT co.ComandaID) AS nrcomenzi,
        SUM(d.TotalLinie) AS totalvanzari,
        ROUND(SUM(d.TotalLinie) / COUNT(DISTINCT co.ComandaID), 2) AS vanzaremediepercomanda
    FROM Client c
    JOIN Comanda co ON c.ClientID = co.ClientID
    JOIN DetaliuComanda d ON co.ComandaID = d.ComandaID
    GROUP BY numeclient
    ORDER BY totalvanzari DESC
    LIMIT 20;
    """
    df = run_query(query)
    st.dataframe(df)

    if not df.empty:
        fig, ax = plt.subplots(figsize=(10, 4))
        sns.barplot(data=df, x="numeclient", y="vanzaremediepercomanda", ax=ax)
        plt.xticks(rotation=45)
        st.pyplot(fig)

# ===============================
# 8️⃣ Clienți fideli
# ===============================
elif menu == "8️⃣ Clienți fideli":
    st.subheader("Cei mai fideli clienți în funcție de gen muzical")

    query = """
    SELECT 
        cat.Nume AS genmuzical,
        INITCAP(c.Prenume || ' ' || c.Nume) AS client,
        COUNT(DISTINCT co.ComandaID) AS nrcomenzi,
        ROUND(SUM(d.TotalLinie), 2) AS totalvanzari
    FROM Client c
    JOIN Comanda co ON c.ClientID = co.ClientID
    JOIN DetaliuComanda d ON co.ComandaID = d.ComandaID
    JOIN Produs p ON d.ProdusID = p.ProdusID
    JOIN CategorieProdus cat ON p.CategorieProdusID = cat.CategorieProdusID
    GROUP BY cat.Nume, client
    HAVING COUNT(DISTINCT co.ComandaID) >= 5
    ORDER BY totalvanzari DESC
    LIMIT 30;
    """
    df = run_query(query)
    st.dataframe(df)

    if not df.empty:
        fig, ax = plt.subplots(figsize=(10, 5))
        sns.barplot(data=df, x="client", y="totalvanzari", hue="genmuzical", ax=ax)
        plt.xticks(rotation=45)
        st.pyplot(fig)

# ===============================
# 9️⃣ Profitabilitate pe gen și oraș
# ===============================
elif menu == "9️⃣ Profitabilitate pe gen și oraș":
    st.subheader("Analiza profitabilității pe gen muzical și oraș")

    query = """
    SELECT 
        cat.Nume AS genmuzical,
        c.Oras AS oras,
        ROUND(SUM(d.TotalLinie), 2) AS totalvanzari,
        COUNT(DISTINCT co.ComandaID) AS nrcomenzi,
        ROUND(SUM(d.TotalLinie) / COUNT(DISTINCT co.ComandaID), 2) AS mediepercomanda
    FROM Client c
    JOIN Comanda co ON c.ClientID = co.ClientID
    JOIN DetaliuComanda d ON co.ComandaID = d.ComandaID
    JOIN Produs p ON d.ProdusID = p.ProdusID
    JOIN CategorieProdus cat ON p.CategorieProdusID = cat.CategorieProdusID
    GROUP BY cat.Nume, c.Oras
    ORDER BY totalvanzari DESC;
    """
    df = run_query(query)
    st.dataframe(df)

    if not df.empty:
        fig, ax = plt.subplots(figsize=(10, 5))
        sns.barplot(data=df, x="genmuzical", y="totalvanzari", hue="oras", ax=ax)
        plt.xticks(rotation=45)
        st.pyplot(fig)
