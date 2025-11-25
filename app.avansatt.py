import streamlit as st
import pandas as pd
import psycopg2
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from io import BytesIO
from math import radians, sin, cos, sqrt, atan2

# pentru harta
import folium
from streamlit_folium import st_folium
from folium.plugins import HeatMap

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
# FUNCȚII UTILE
# =========================
def distance_km(coord1, coord2):
    """Calculează distanța aproximativă (great-circle) între 2 coordonate (lat, lon)."""
    R = 6371.0  # raza Pământului în km
    lat1, lon1 = coord1
    lat2, lon2 = coord2
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return R * c

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
st.sidebar.header("Filtre")

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
        "Predicție (istoric)",
        "Hartă vânzări pe orașe",
        "Distribuție genuri",
        "Export HTML raport"
    ],
    index=0
)

# =========================
# HELPER EXPORT CSV+EXCEL SIMPLU
# =========================
def export_downloads(df, filename_prefix="export"):
    c1, c2 = st.columns(2)
    csv_bytes = df.to_csv(index=False).encode("utf-8")
    c1.download_button("Descarcă CSV", data=csv_bytes,
                       file_name=f"{filename_prefix}.csv", mime="text/csv")
    try:
        bio = BytesIO()
        with pd.ExcelWriter(bio, engine="xlsxwriter") as writer:
            df.to_excel(writer, sheet_name="Date", index=False)
        c2.download_button(
            "Descarcă Excel",
            data=bio.getvalue(),
            file_name=f"{filename_prefix}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    except Exception:
        c2.info("Pentru Excel, instalează `xlsxwriter`.")

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
        SUM(d.TotalLinie) AS TotalVanzari
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
        sns.barplot(data=df, x="genmuzical", y="totalvanzari",
                    hue="grupvarsta", ax=ax)
        plt.xticks(rotation=45)
        st.pyplot(fig)

# =========================
# 2) EVOLUȚIA VÂNZĂRILOR PE LUNI (cu Min/Max colorat)
# =========================
elif view == "Evoluția vânzărilor pe luni":
    df = f.groupby(["luna", "gen"], as_index=False)["total"].sum() \
          .rename(columns={"total": "totalvanzari", "gen": "genmuzical"})
    st.dataframe(df.sort_values("luna"))
    export_downloads(df, "evolutie_lunara")

    if not df.empty:
        fig, ax = plt.subplots(figsize=(10, 5))
        sns.lineplot(data=df, x="luna", y="totalvanzari",
                     hue="genmuzical", marker="o", ax=ax)
        plt.xticks(rotation=45)

        # Highlight Min & Max per gen
        for g in df["genmuzical"].unique():
            sub = df[df["genmuzical"] == g]
            if sub.empty:
                continue
            min_row = sub.loc[sub["totalvanzari"].idxmin()]
            max_row = sub.loc[sub["totalvanzari"].idxmax()]
            ax.scatter(min_row["luna"], min_row["totalvanzari"],
                       color="red", s=120)
            ax.scatter(max_row["luna"], max_row["totalvanzari"],
                       color="green", s=120)

        st.pyplot(fig)

        rez = []
        for g in df["genmuzical"].unique():
            sub = df[df["genmuzical"] == g]
            rez.append({
                "Gen muzical": g,
                "Luna MIN": sub.loc[sub["totalvanzari"].idxmin()]["luna"],
                "Valoare MIN": sub["totalvanzari"].min(),
                "Luna MAX": sub.loc[sub["totalvanzari"].idxmax()]["luna"],
                "Valoare MAX": sub["totalvanzari"].max()
            })
        st.markdown("### Puncte Minime și Maxime Identificate")
        st.dataframe(pd.DataFrame(rez))

# =========================
# 3) NECESAR APROVIZIONARE
# =========================
elif view == "Necesar aprovizionare (suport)":
    df = f.groupby("suport", as_index=False).agg(totalvandut=("cantitate", "sum"))
    zile = max((pd.to_datetime(end_date) - pd.to_datetime(start_date)).days, 1)
    df["necesarestimativ"] = (df["totalvandut"] / zile * 30 * 1.15).round(0)
    st.dataframe(df)
    export_downloads(df, "necesar_aprovizionare")
    if not df.empty:
        fig, ax = plt.subplots(figsize=(7, 4))
        sns.barplot(data=df, x="suport", y="necesarestimativ", ax=ax)
        st.pyplot(fig)

# =========================
# 4) EVENIMENTE (±3 zile)
# =========================
elif view == "Evenimente (fereastră ±3 zile)":
    q = """
    SELECT 
        e.Nume AS eveniment,
        e.DataEveniment AS dataeveniment,
        SUM(d.TotalLinie) AS total_vanzari,
        COUNT(co.ComandaID) AS nr_comenzi
    FROM Eveniment e
    LEFT JOIN Comanda co 
        ON co.DataComanda BETWEEN e.DataEveniment - INTERVAL '3 days'
                            AND e.DataEveniment + INTERVAL '3 days'
    LEFT JOIN DetaliuComanda d 
        ON co.ComandaID = d.ComandaID
    WHERE co.DataComanda BETWEEN %(start)s AND %(end)s
    GROUP BY e.Nume, e.DataEveniment
    ORDER BY e.DataEveniment;
    """
    df = run_query(q, {"start": start_date, "end": end_date})
    df.columns = [c.lower() for c in df.columns]

    st.dataframe(df)
    export_downloads(df, "evenimente")

    if df.empty:
        st.warning("Nu există vânzări asociate evenimentelor în perioada selectată.")
    else:
        fig, ax = plt.subplots(figsize=(12, 4))
        bars = ax.bar(df["eveniment"], df["total_vanzari"])
        plt.xticks(rotation=45)

        max_val, min_val = df["total_vanzari"].max(), df["total_vanzari"].min()
        for bar, val in zip(bars, df["total_vanzari"]):
            if val == max_val:
                bar.set_color("green")
            elif val == min_val:
                bar.set_color("red")

        st.pyplot(fig)
        st.success(f"📈 Maxim: **{max_val:.2f} RON**  | 🔻 Minim: **{min_val:.2f} RON**")

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
    df = f.groupby(["gen"], as_index=False)["cantitate"].sum().rename(columns={"cantitate": "totalvandut"})
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
    df = f.groupby(["gen", "oras"], as_index=False)["total"].sum().rename(columns={"total": "totalvanzari"})
    st.dataframe(df.sort_values("totalvanzari", ascending=False))
    export_downloads(df, "profit_gen_oras")
    if not df.empty:
        fig, ax = plt.subplots(figsize=(10, 5))
        sns.barplot(data=df, x="gen", y="totalvanzari", hue="oras", ax=ax)
        plt.xticks(rotation=45)
        st.pyplot(fig)

# =========================
# 10) PREVIZIUNE ISTORICĂ + EXPORT EXCEL TRENDLINE
# =========================
elif view == "Predicție (istoric)":
    st.subheader("Predicție bazată pe istoricul ultimelor 3 luni")

    df = f.groupby("luna", as_index=False)["total"].sum().rename(columns={"total": "totalvanzari"})
    df = df.sort_values("luna")

    if df.shape[0] >= 3:
        last_3 = df.tail(3)["totalvanzari"]
        predict_value = round(last_3.mean(), 2)

        last_month = df["luna"].max()
        next_month = last_month + pd.offsets.MonthBegin(1)

        if next_month.year == 2023:
            fut = pd.DataFrame({"luna": [next_month], "totalvanzari_pred": [predict_value]})

            fig, ax = plt.subplots(figsize=(10, 5))
            sns.lineplot(data=df, x="luna", y="totalvanzari", marker="o",
                         label="Istoric", ax=ax)
            sns.scatterplot(data=fut, x="luna", y="totalvanzari_pred",
                            color="purple", s=150, label="Previziune")
            plt.xticks(rotation=45)
            ax.legend()
            st.pyplot(fig)

            st.success(f"Previziunea pentru {next_month.strftime('%b %Y')}: **{predict_value} RON**")
            st.dataframe(fut.rename(columns={"totalvanzari_pred": "Estimat"}))
        else:
            st.info("Nu mai există luni rămase în 2023 pentru previziune.")
    else:
        st.warning("Ai nevoie de cel puțin 3 luni de date pentru predicție.")

    # --- Export Excel avansat cu trendline, R² și conditional formatting ---
    if not df.empty:
        st.markdown("### Export Excel cu grafic, trendline și formatări")
        if st.button("Creează fișier Excel de predicție"):
            try:
                bio = BytesIO()
                with pd.ExcelWriter(bio, engine="xlsxwriter") as writer:
                    df_excel = df.copy()
                    # transformăm luna în text pentru afișare
                    df_excel["luna_text"] = df_excel["luna"].dt.strftime("%Y-%m")
                    df_excel = df_excel[["luna_text", "totalvanzari"]]
                    df_excel.columns = ["Luna", "TotalVanzari"]

                    # scriem datele începând cu rândul 2 (rândul 1 = header titlu)
                    df_excel.to_excel(writer, sheet_name="Istoric", index=False, startrow=1)
                    workbook = writer.book
                    worksheet = writer.sheets["Istoric"]

                    # titlu raport
                    worksheet.write(0, 0, "Evoluție vânzări lunare (raport BI)")

                    last_row = len(df_excel) + 1  # +1 pentru header

                    # total pe coloană (formulă)
                    worksheet.write(last_row + 1, 0, "Total")
                    worksheet.write_formula(last_row + 1, 1, f"=SUM(B3:B{last_row+1})")

                    # formatări de bază
                    bold = workbook.add_format({"bold": True})
                    money = workbook.add_format({"num_format": "#,##0.00"})
                    worksheet.set_column("A:A", 12)
                    worksheet.set_column("B:B", 15, money)
                    worksheet.set_row(0, 18, bold)

                    # conditional formatting (3 color scale)
                    worksheet.conditional_format(2, 1, last_row + 1, 1, {
                        "type": "3_color_scale"
                    })

                    # grafic cu trendline și R²
                    chart = workbook.add_chart({"type": "line"})
                    chart.add_series({
                        "name": "Total vânzări",
                        "categories": ["Istoric", 2, 0, last_row + 1, 0],  # A3:A...
                        "values": ["Istoric", 2, 1, last_row + 1, 1],      # B3:B...
                        "trendline": {
                            "type": "linear",
                            "display_r_squared": True,
                            "display_equation": False
                        },
                    })
                    chart.set_title({"name": "Evoluție vânzări & trendline"})
                    chart.set_x_axis({"name": "Luna"})
                    chart.set_y_axis({"name": "Vânzări (RON)"})
                    chart.set_legend({"position": "bottom"})

                    worksheet.insert_chart("D3", chart)

                st.download_button(
                    "⬇Descarcă Excel cu trendline",
                    data=bio.getvalue(),
                    file_name="predictie_trendline.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            except Exception as e:
                st.error(f"A apărut o eroare la generarea fișierului Excel: {e}")

# =========================
# 11) Hartă interactivă orașe (Heatmap + Bubbles + distanțe)
# =========================
elif view == "Hartă vânzări pe orașe":
    st.subheader("Hartă interactivă a vânzărilor pe orașe")

    df = f.groupby("oras", as_index=False)["total"].sum().rename(columns={"total": "totalvanzari"})

    if df.empty:
        st.warning("Nu există date pentru perioada selectată.")
    else:
        # Orașele tale din baza de date (din scriptul de generare)
        coordonate = {
            "Bucuresti": (44.4268, 26.1025),
            "Cluj": (46.7712, 23.6236),
            "Timisoara": (45.7489, 21.2087),
            "Iasi": (47.1585, 27.6014)
        }

        df["lat"] = df["oras"].map(lambda x: coordonate.get(x, (45, 25))[0])
        df["lon"] = df["oras"].map(lambda x: coordonate.get(x, (45, 25))[1])

        m = folium.Map(location=[45.5, 25], zoom_start=6, tiles="CartoDB positron")

        # Heatmap pe baza vânzărilor
        heat_data = df[["lat", "lon", "totalvanzari"]].values.tolist()
        HeatMap(heat_data, radius=25, blur=15, max_zoom=6).add_to(m)

        # Bubbles dimensionate după vânzări
        for _, row in df.iterrows():
            folium.CircleMarker(
                location=(row["lat"], row["lon"]),
                radius=5 + row["totalvanzari"] / df["totalvanzari"].max() * 15,
                popup=f"{row['oras']} — {row['totalvanzari']:.2f} RON",
                color="purple",
                fill=True,
                fill_color="purple",
                fill_opacity=0.7
            ).add_to(m)

        st_folium(m, width=900, height=550)
        st.dataframe(df)
        export_downloads(df, "harta_orase")

        # Export hartă HTML (fișier fizic)
        if st.button("Export hartă HTML"):
            m.save("harta_interactiva_vanzari.html")
            st.success("Harta a fost salvată ca harta_interactiva_vanzari.html în folderul proiectului.")

        # Calcul distanță între orașe (similar cu exercițiul MapPoint - route & distance)
        st.markdown("### 📐 Distanță aproximativă între două orașe")
        orase_disponibile = [o for o in df["oras"].unique() if o in coordonate.keys()]
        if len(orase_disponibile) >= 2:
            c1, c2 = st.columns(2)
            oras1 = c1.selectbox("Oraș plecare", orase_disponibile, key="oras_start")
            oras2 = c2.selectbox("Oraș destinație", orase_disponibile, key="oras_stop")

            if st.button("Calculează distanța (km)"):
                coord1 = coordonate.get(oras1)
                coord2 = coordonate.get(oras2)
                if coord1 and coord2:
                    dist = distance_km(coord1, coord2)
                    st.success(f"Distanța aproximativă între **{oras1}** și **{oras2}** este de **{dist:.1f} km**.")
        else:
            st.info("Sunt necesare cel puțin 2 orașe cu coordonate definite pentru a calcula distanța.")

# =========================
# 12) Donut Chart genuri muzicale
# =========================
elif view == "Distribuție genuri":
    st.subheader("Distribuția vânzărilor pe genuri muzicale")

    df = f.groupby("gen", as_index=False)["total"].sum().rename(columns={"total": "totalvanzari"})

    if df.empty:
        st.warning("Nu există date în intervalul selectat.")
    else:
        fig, ax = plt.subplots(figsize=(6, 6))
        wedges, texts, autotexts = ax.pie(
            df["totalvanzari"],
            labels=df["gen"],
            autopct="%1.1f%%",
            startangle=90,
            wedgeprops={'width': 0.3}
        )
        ax.set_title("Distribuție vânzări pe genuri - DONUT CHART")
        st.pyplot(fig)

        st.dataframe(df)
        export_downloads(df, "distributie_genuri")

# =========================
# 13) EXPORT HTML RAPORT
# =========================
elif view == "Export HTML raport":
    st.subheader("Export HTML – raport vânzări pe genuri (tip foaie web)")

    df = f.groupby("gen", as_index=False)["total"].sum().rename(columns={"total": "totalvanzari"})
    if df.empty:
        st.warning("Nu există date în intervalul selectat.")
    else:
        # construim un mic raport HTML cu CSS
        html_table = df.to_html(index=False, classes="tabel-bi", border=0)
        html_doc = f"""
<!DOCTYPE html>
<html lang="ro">
<head>
    <meta charset="UTF-8">
    <title>Raport vânzări pe genuri</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 40px;
            background-color: #f5f5f5;
        }}
        h1 {{
            text-align: center;
            color: #333;
        }}
        .tabel-bi {{
            border-collapse: collapse;
            width: 70%;
            margin: 20px auto;
            background-color: #ffffff;
        }}
        .tabel-bi thead tr {{
            background-color: #4a90e2;
            color: #ffffff;
        }}
        .tabel-bi th, .tabel-bi td {{
            border: 1px solid #ddd;
            padding: 8px 12px;
            text-align: center;
        }}
        .tabel-bi tr:nth-child(even) {{
            background-color: #f2f2f2;
        }}
        .tabel-bi tr:hover {{
            background-color: #e6f2ff;
        }}
        .footer {{
            text-align: center;
            margin-top: 30px;
            color: #666;
        }}
    </style>
</head>
<body>
    <h1>Raport vânzări pe genuri muzicale</h1>
    {html_table}
    <div class="footer">
        Generat automat din aplicația Streamlit – proiect BI muzică
    </div>
</body>
</html>
"""
        st.markdown("Preview cod HTML (primele 400 caractere):")
        st.code(html_doc[:400] + "...\n", language="html")

        st.download_button(
            "Descarcă raport HTML",
            data=html_doc.encode("utf-8"),
            file_name="raport_vanzari_genuri.html",
            mime="text/html"
        )
