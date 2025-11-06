import streamlit as st
import pandas as pd
import psycopg2
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from io import BytesIO
from sklearn.linear_model import LinearRegression

# =========================
# CONFIG BAZĂ DE DATE
# =========================
DB_CONFIG = {
    "host": "localhost",
    "dbname": "muzica",
    "user": "postgres",
    "password": "123"
}

@st.cache_data
def run_query(query, params=None):
    conn = psycopg2.connect(**DB_CONFIG)
    df = pd.read_sql(query, conn, params=params)
    conn.close()
    df.columns = [c.lower() for c in df.columns]
    return df

# =========================
# SETĂRI PAGINĂ
# =========================
st.set_page_config(page_title="Dashboard muzică", layout="wide")
st.title("Dashboard muzică")

# =========================
# ÎNCĂRCARE DATE DE BAZĂ (FACT)
# =========================
core_q = """
SELECT 
    co.DataComanda AS Data,
    cat.Nume AS Gen,
    c.Oras AS Oras,
    p.TipSuport AS Suport,
    d.Cantitate AS Cantitate,
    d.TotalLinie AS Total
FROM DetaliuComanda d
JOIN Comanda co ON d.ComandaID = co.ComandaID
JOIN Produs p ON d.ProdusID = p.ProdusID
JOIN CategorieProdus cat ON p.CategorieProdusID = cat.CategorieProdusID
JOIN Client c ON co.ClientID = c.ClientID;
"""
core = run_query(core_q)
core["data"] = pd.to_datetime(core["data"])
core["an"] = core["data"].dt.year
core["luna"] = core["data"].dt.to_period("M").dt.to_timestamp()
core["month_name"] = core["data"].dt.strftime("%b")

# =========================
# FILTRE LATERALE
# =========================
st.sidebar.header("🔎 Filtre globale")

genuri = ["Toate"] + sorted(core["gen"].dropna().unique().tolist())
orase = ["Toate"] + sorted(core["oras"].dropna().unique().tolist())

gen_sel = st.sidebar.selectbox("Gen muzical", genuri, index=0)
oras_sel = st.sidebar.selectbox("Oraș", orase, index=0)

min_date_2023 = pd.Timestamp("2023-01-01")
max_date_2023 = pd.Timestamp("2023-12-31")
date_range = st.sidebar.date_input(
    "Perioadă (doar 2023)",
    (min_date_2023, max_date_2023),
    min_value=min_date_2023, max_value=max_date_2023
)
if isinstance(date_range, tuple):
    start_date, end_date = date_range
else:
    start_date, end_date = min_date_2023, max_date_2023

# aplicare filtre
f = core.copy()
f = f[(f["data"] >= pd.to_datetime(start_date)) & (f["data"] <= pd.to_datetime(end_date))]
if gen_sel != "Toate":
    f = f[f["gen"] == gen_sel]
if oras_sel != "Toate":
    f = f[f["oras"] == oras_sel]

# =========================
# KPI-URI
# =========================
col1, col2, col3, col4 = st.columns(4)
col1.metric("Vânzări filtrate (RON)", round(float(f["total"].sum()), 2))
col2.metric("Nr. linii vânzare", int(f.shape[0]))
col3.metric("Genuri unice", int(f["gen"].nunique()))
col4.metric("Orașe unice", int(f["oras"].nunique()))

# =========================
# MENIU ANALIZE
# =========================
view = st.selectbox(
    "Alege analiza",
    [
        "Asocieri vânzări-genuri",
        "Evoluția vânzărilor pe luni",
        "Necesar aprovizionare (suport)",
        "Evenimente (fereastră ±3 zile)",
        "Impact promoții (estimare)",
        "Top produse (după gen)",
        "Vânzări medii pe client",
        "Clienți fideli (>=5 comenzi)",
        "Profitabilitate gen x oraș",
        "Predicție & Comparare"
    ],
    index=0
)

# =========================
# HELPER EXPORT
# =========================
def export_downloads(df, filename_prefix="export"):
    c1, c2 = st.columns(2)
    csv_bytes = df.to_csv(index=False).encode("utf-8")
    c1.download_button("📄 Descarcă CSV", data=csv_bytes, file_name=f"{filename_prefix}.csv", mime="text/csv")
    try:
        bio = BytesIO()
        with pd.ExcelWriter(bio, engine="xlsxwriter") as writer:
            df.to_excel(writer, sheet_name="Date", index=False)
        c2.download_button(
            "💾 Descarcă Excel",
            data=bio.getvalue(),
            file_name=f"{filename_prefix}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    except Exception:
        c2.info("Pentru Excel, instalează opțional pachetul `xlsxwriter`.")

# =========================
# 1) ASOCIERI VÂNZĂRI–GENURI
# =========================
if view == "Asocieri vânzări-genuri":
    q = """
    SELECT 
        CASE 
            WHEN EXTRACT(YEAR FROM AGE(CURRENT_DATE, c.DataNasterii)) BETWEEN 18 AND 24 THEN '18-24 ani'
            WHEN EXTRACT(YEAR FROM AGE(CURRENT_DATE, c.DataNasterii)) BETWEEN 25 AND 45 THEN '25-45 ani'
            WHEN EXTRACT(YEAR FROM AGE(CURRENT_DATE, c.DataNasterii)) BETWEEN 46 AND 65 THEN '46-65 ani'
            ELSE '65+ ani'
        END AS GrupVarsta,
        c.NivelStudii,
        cat.Nume AS GenMuzical,
        SUM(d.TotalLinie) AS TotalVanzari,
        MIN(co.DataComanda) AS DMin,
        MAX(co.DataComanda) AS DMax
    FROM Client c
    JOIN Comanda co ON c.ClientID = co.ClientID
    JOIN DetaliuComanda d ON co.ComandaID = d.ComandaID
    JOIN Produs p ON d.ProdusID = p.ProdusID
    JOIN CategorieProdus cat ON p.CategorieProdusID = cat.CategorieProdusID
    WHERE co.DataComanda BETWEEN %(start)s AND %(end)s
    GROUP BY GrupVarsta, c.NivelStudii, cat.Nume
    ORDER BY TotalVanzari DESC;
    """
    df = run_query(q, {"start": start_date, "end": end_date})
    st.dataframe(df)
    export_downloads(df, "asocieri")

    if not df.empty:
        fig, ax = plt.subplots(figsize=(10, 5))
        sns.barplot(data=df, x="genmuzical", y="totalvanzari", hue="grupvarsta", ax=ax)
        plt.xticks(rotation=45)
        st.pyplot(fig)

# =========================
# 2) EVOLUȚIA VÂNZĂRILOR PE LUNI
# =========================
elif view == "Evoluția vânzărilor pe luni":
    df = f.groupby(["luna", "gen"], as_index=False)["total"].sum() \
          .rename(columns={"total": "totalvanzari", "gen": "genmuzical"})

    st.dataframe(df.sort_values("luna"))
    export_downloads(df, "evolutie_lunara")

    if not df.empty:
        fig, ax = plt.subplots(figsize=(10, 5))
        sns.lineplot(data=df, x="luna", y="totalvanzari", hue="genmuzical", marker="o", ax=ax)
        plt.xticks(rotation=45)
        st.pyplot(fig)

        # Heatmap gen x lună
        st.markdown("### Heatmap gen x lună")
        piv = df.copy()
        piv["luna_num"] = piv["luna"].dt.month
        heat = piv.pivot_table(values="totalvanzari", index="genmuzical", columns="luna_num",
                               aggfunc="sum", fill_value=0)
        fig2, ax2 = plt.subplots(figsize=(10, 6))
        sns.heatmap(heat, annot=False, ax=ax2)
        ax2.set_xlabel("Luna (1–12)")
        st.pyplot(fig2)

# =========================
# 3) NECESAR APROVIZIONARE
# =========================
elif view == "Necesar aprovizionare (suport)":
    df = f.groupby("suport", as_index=False).agg(totalvandut=("cantitate", "sum"))
    # aproximație: necesar pentru o lună pe baza intensității intervalului selectat + buffer 15%
    zile = max((pd.to_datetime(end_date) - pd.to_datetime(start_date)).days, 1)
    df["necesarestimativ"] = (df["totalvandut"] / zile * 30 * 1.15).round(0)

    st.dataframe(df)
    export_downloads(df, "necesar_aprovizionare")

    if not df.empty:
        fig, ax = plt.subplots(figsize=(7, 4))
        sns.barplot(data=df, x="suport", y="necesarestimativ", ax=ax)
        st.pyplot(fig)

# =========================
# 4) EVENIMENTE (±3 ZILE)
# =========================
elif view == "Evenimente (±3 zile)":
    q = """
    SELECT 
        e.Nume AS Eveniment,
        e.DataEveniment AS DataEveniment,
        SUM(d.TotalLinie) AS TotalVanzari
    FROM Eveniment e
    JOIN Comanda co ON co.DataComanda BETWEEN e.DataEveniment - INTERVAL '3 days'
                                      AND e.DataEveniment + INTERVAL '3 days'
    JOIN DetaliuComanda d ON co.ComandaID = d.ComandaID
    WHERE e.DataEveniment BETWEEN %(start)s AND %(end)s
    GROUP BY e.Nume, e.DataEveniment
    ORDER BY e.DataEveniment;
    """
    df = run_query(q, {"start": start_date, "end": end_date})
    st.dataframe(df)
    export_downloads(df, "evenimente")

    if not df.empty:
        fig, ax = plt.subplots(figsize=(10, 4))
        sns.barplot(data=df, x="eveniment", y="totalvanzari", ax=ax)
        plt.xticks(rotation=45)
        st.pyplot(fig)
# =========================
# 5) IMPACT PROMOȚII (ESTIMARE)
# =========================
elif view == "Impact promoții (estimare)":
    q = """
    SELECT 
        p.Nume AS Produs,
        cat.Nume AS GenMuzical,
        pr.Reducere AS ReducereProcent,
        SUM(d.Cantitate) AS CantitateVanduta,
        ROUND(SUM(d.TotalLinie), 2) AS TotalVanzariActuale,
        ROUND(SUM(d.TotalLinie) * (1 + (pr.Reducere / 100.0) * 0.5), 2) AS TotalVanzariEstimate
    FROM DetaliuComanda d
    JOIN Produs p ON d.ProdusID = p.ProdusID
    JOIN CategorieProdus cat ON p.CategorieProdusID = cat.CategorieProdusID
    JOIN Promotie pr ON p.ProdusID = pr.ProdusID
    WHERE pr.DataStart <= %(end)s AND pr.DataEnd >= %(start)s
    GROUP BY p.Nume, cat.Nume, pr.Reducere
    ORDER BY TotalVanzariEstimate DESC
    LIMIT 50;
    """
    df = run_query(q, {"start": start_date, "end": end_date})
    st.dataframe(df)
    export_downloads(df, "impact_promotii")

    if not df.empty:
        fig, ax = plt.subplots(figsize=(10, 4))
        sns.scatterplot(data=df, x="reducereprocent", y="totalvanzariestimate",
                        hue="genmuzical", s=120, ax=ax)
        st.pyplot(fig)

# =========================
# 6) TOP PRODUSE (DUPĂ GEN)
# =========================
elif view == "Top produse (după gen)":
    # top la nivel de GEN (din filtrul curent)
    df = f.groupby(["gen"], as_index=False)["cantitate"].sum() \
          .rename(columns={"cantitate": "totalvandut"})
    st.dataframe(df.sort_values("totalvandut", ascending=False))
    export_downloads(df, "top_produse_pe_gen")

    if not df.empty:
        fig, ax = plt.subplots(figsize=(10, 4))
        sns.barplot(data=df, x="gen", y="totalvandut", ax=ax)
        plt.xticks(rotation=45)
        st.pyplot(fig)

# =========================
# 7) VÂNZĂRI MEDII PE CLIENT
# =========================
elif view == "Vânzări medii pe client":
    q = """
    SELECT
        INITCAP(c.Prenume || ' ' || c.Nume) AS NumeClient,
        COUNT(DISTINCT co.ComandaID) AS NrComenzi,
        SUM(d.TotalLinie) AS TotalVanzari,
        ROUND(SUM(d.TotalLinie) / COUNT(DISTINCT co.ComandaID), 2) AS VanzareMediePerComanda
    FROM Client c
    JOIN Comanda co ON c.ClientID = co.ClientID
    JOIN DetaliuComanda d ON co.ComandaID = d.ComandaID
    WHERE co.DataComanda BETWEEN %(start)s AND %(end)s
    GROUP BY NumeClient
    ORDER BY TotalVanzari DESC
    LIMIT 30;
    """
    df = run_query(q, {"start": start_date, "end": end_date})
    st.dataframe(df)
    export_downloads(df, "vanzari_medii_client")

    if not df.empty:
        fig, ax = plt.subplots(figsize=(10, 4))
        sns.barplot(data=df, x="numeclient", y="vanzaremediepercomanda", ax=ax)
        plt.xticks(rotation=45)
        st.pyplot(fig)

# =========================
# 8) CLIENȚI FIDELI (>=5 COMENZI)
# =========================
elif view == "Clienți fideli (>=5 comenzi)":
    q = """
    WITH V AS (
        SELECT 
            c.ClientID,
            INITCAP(c.Prenume || ' ' || c.Nume) AS Client,
            COUNT(DISTINCT co.ComandaID) AS NrComenzi,
            SUM(d.TotalLinie) AS TotalVanzari
        FROM Client c
        JOIN Comanda co ON c.ClientID = co.ClientID
        JOIN DetaliuComanda d ON co.ComandaID = d.ComandaID
        WHERE co.DataComanda BETWEEN %(start)s AND %(end)s
        GROUP BY c.ClientID, Client
    )
    SELECT * FROM V WHERE NrComenzi >= 5 ORDER BY TotalVanzari DESC;
    """
    df = run_query(q, {"start": start_date, "end": end_date})
    st.dataframe(df)
    export_downloads(df, "clienti_fideli")

    if not df.empty:
        fig, ax = plt.subplots(figsize=(10, 5))
        sns.barplot(data=df, x="client", y="totalvanzari", ax=ax)
        plt.xticks(rotation=45)
        st.pyplot(fig)
# =========================
# 9) PROFITABILITATE GEN x ORAȘ
# =========================
elif view == "Profitabilitate gen x oraș":
    df = f.groupby(["gen", "oras"], as_index=False)["total"].sum() \
          .rename(columns={"total": "totalvanzari"})
    st.dataframe(df.sort_values("totalvanzari", ascending=False))
    export_downloads(df, "profit_gen_oras")

    if not df.empty:
        fig, ax = plt.subplots(figsize=(10, 5))
        sns.barplot(data=df, x="gen", y="totalvanzari", hue="oras", ax=ax)
        plt.xticks(rotation=45)
        st.pyplot(fig)

# =========================
# 10) PREDICȚIE & COMPARARE
# =========================
elif view == "Predicție & Comparare":
    st.subheader("Predicție simplă (regresie liniară) + comparare între luni")

    # agregare lunară globală pe filtrul curent
    df = f.groupby("luna", as_index=False)["total"].sum().rename(columns={"total": "totalvanzari"})
    st.dataframe(df.sort_values("luna"))
    export_downloads(df, "serie_lunara_filtrata")

    if df.shape[0] >= 3:
        # pregătim X, y (index lunar 1..n)
        df = df.sort_values("luna").reset_index(drop=True)
        df["t"] = np.arange(1, len(df) + 1)
        X = df[["t"]].values
        y = df["totalvanzari"].values

        model = LinearRegression()
        model.fit(X, y)

        # prezicem următoarele 3 luni, dar capăm să rămânem în 2023
        last_month = df["luna"].max()
        future_months = []
        for k in range(1, 4):
            nxt = (last_month + pd.offsets.MonthBegin(k))
            if nxt.year == 2023:
                future_months.append(nxt)
        if future_months:
            t_future = np.arange(len(df) + 1, len(df) + 1 + len(future_months)).reshape(-1, 1)
            y_pred = model.predict(t_future)

            fut = pd.DataFrame({
                "luna": future_months,
                "totalvanzari_pred": y_pred
            })

            # grafic comparativ
            fig, ax = plt.subplots(figsize=(10, 5))
            sns.lineplot(data=df, x="luna", y="totalvanzari", marker="o", label="Istoric", ax=ax)
            sns.lineplot(data=fut, x="luna", y="totalvanzari_pred", marker="o", label="Predicție", ax=ax)
            plt.xticks(rotation=45)
            st.pyplot(fig)

            st.success("Predicția a fost calculată pe baza regresiei liniare.")
            st.dataframe(fut)
            export_downloads(fut.rename(columns={"totalvanzari_pred": "totalvanzari"}), "predictie_lunara")
        else:
            st.info("Toate lunile disponibile sunt până în decembrie 2023; nu mai există luni viitoare în 2023 pentru predicție.")
    else:
        st.warning("Ai nevoie de cel puțin 3 luni de date în intervalul selectat pentru a calcula o predicție.")

    st.markdown("###Comparare între luni (bar chart)")
    if not df.empty:
        df_bar = f.groupby(f["data"].dt.month, as_index=False)["total"].sum().rename(columns={"data": "luna_idx", "total": "totalvanzari"})
        df_bar = df_bar.rename(columns={"data": "luna_idx", 0: "luna_idx"})
        df_bar["luna_idx"] = df_bar["luna"]
        fig3, ax3 = plt.subplots(figsize=(10, 4))
        sns.barplot(data=df_bar, x="luna_idx", y="totalvanzari", ax=ax3)
        ax3.set_xlabel("Luna (1–12)")
        st.pyplot(fig3)
