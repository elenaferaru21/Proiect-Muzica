CREATE TABLE Client (
    ClientID SERIAL PRIMARY KEY,
    Prenume VARCHAR(50),
    Nume VARCHAR(50),
    DataNasterii DATE,
    NivelStudii VARCHAR(50),
    Oras VARCHAR(50)
);

INSERT INTO Client (Prenume, Nume, DataNasterii, NivelStudii, Oras)
SELECT
    'Prenume' || i,
    'Nume' || i,
    DATE '1970-01-01' + (random()*20000)::int,
    CASE WHEN random() < 0.5 THEN 'Liceu' ELSE 'Universitate' END,
    CASE WHEN random() < 0.5 THEN 'Bucuresti' 
         WHEN random() < 0.7 THEN 'Cluj'
         WHEN random() < 0.85 THEN 'Timisoara'
         ELSE 'Iasi' END
FROM generate_series(1,5000) AS s(i);

CREATE TABLE CategorieProdus (
    CategorieProdusID SERIAL PRIMARY KEY,
    Nume VARCHAR(50)
);

INSERT INTO CategorieProdus (Nume) VALUES
('Rock'),('Pop'),('Jazz'),('Hip-Hop'),('Clasica'),
('Electronica'),('Metal'),('Reggae'),('Folk'),('Country');

CREATE TABLE Produs (
    ProdusID SERIAL PRIMARY KEY,
    Nume VARCHAR(100),
    CategorieProdusID INT REFERENCES CategorieProdus(CategorieProdusID),
    TipSuport VARCHAR(20),
    Pret NUMERIC(6,2)
);

INSERT INTO Produs (Nume, CategorieProdusID, TipSuport, Pret)
SELECT
    'Album ' || i,
    (1 + floor(random()*10))::int,
    CASE WHEN random() < 0.5 THEN 'CD'
         WHEN random() < 0.8 THEN 'DVD'
         ELSE 'Caseta' END,
    (10 + random()*40)::numeric(6,2)
FROM generate_series(1,500) AS s(i);

CREATE TABLE Comanda (
    ComandaID SERIAL PRIMARY KEY,
    ClientID INT REFERENCES Client(ClientID),
    DataComanda DATE,
    Total NUMERIC(8,2)
);

-- Inserare comenzi (poți să rulezi în două loturi dacă vrei să nu se blocheze pgAdmin)
INSERT INTO Comanda (ClientID, DataComanda, Total)
SELECT
    (1 + floor(random()*5000))::int,
    DATE '2023-01-01' + (random()*365)::int,
    0
FROM generate_series(1,25000) AS s(i);

INSERT INTO Comanda (ClientID, DataComanda, Total)
SELECT
    (1 + floor(random()*5000))::int,
    DATE '2023-01-01' + (random()*365)::int,
    0
FROM generate_series(1,25000) AS s(i);


CREATE TABLE DetaliuComanda (
    DetaliuComandaID SERIAL PRIMARY KEY,
    ComandaID INT REFERENCES Comanda(ComandaID),
    ProdusID INT REFERENCES Produs(ProdusID),
    Cantitate INT,
    TotalLinie NUMERIC(8,2)
);

-- Inserare detalii comenzi rapid
-- 1 detaliu per comandă, pentru toate cele 50.000 comenzi
INSERT INTO DetaliuComanda (ComandaID, ProdusID, Cantitate, TotalLinie)
SELECT
    c.ComandaID,
    (1 + floor(random()*500))::int,
    (1 + floor(random()*5))::int,
    round(((10 + random()*40) * (1 + floor(random()*5)))::numeric,2)
FROM Comanda c;

-- Actualizare total comenzi
UPDATE Comanda co
SET Total = (SELECT SUM(TotalLinie) FROM DetaliuComanda d WHERE d.ComandaID = co.ComandaID);


CREATE TABLE Eveniment (
    EvenimentID SERIAL PRIMARY KEY,
    Nume VARCHAR(100),
    DataEveniment DATE
);

INSERT INTO Eveniment (Nume, DataEveniment)
SELECT
    CASE WHEN random() < 0.3 THEN 'Concert Rock'
         WHEN random() < 0.6 THEN 'Festival Jazz'
         WHEN random() < 0.8 THEN 'Miting'
         ELSE 'Sarbatoare Nationala' END,
    DATE '2023-01-01' + (random()*365)::int
FROM generate_series(1,20) s(i);


CREATE TABLE Promotie (
    PromotieID SERIAL PRIMARY KEY,
    ProdusID INT REFERENCES Produs(ProdusID),
    Reducere NUMERIC(5,2),
    DataStart DATE,
    DataEnd DATE
);

INSERT INTO Promotie (ProdusID, Reducere, DataStart, DataEnd)
SELECT
    (1 + floor(random()*500))::int,
    (5 + random()*30)::numeric(5,2),
    DATE '2023-01-01' + (random()*200)::int,
    DATE '2023-12-31'
FROM generate_series(1,200) s(i);


--1.Interogare asocieri
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
GROUP BY GrupVarsta, c.NivelStudii, cat.Nume
ORDER BY GrupVarsta, c.NivelStudii, TotalVanzari DESC;


--2. Evolutia vanzarilor pe luni
WITH VanzariLunare AS (
    SELECT 
        DATE_TRUNC('month', co.DataComanda) AS Luna,
        cat.Nume AS GenMuzical,
        SUM(d.TotalLinie) AS TotalVanzari
    FROM Comanda co
    JOIN DetaliuComanda d ON co.ComandaID = d.ComandaID
    JOIN Produs p ON d.ProdusID = p.ProdusID
    JOIN CategorieProdus cat ON p.CategorieProdusID = cat.CategorieProdusID
    GROUP BY Luna, cat.Nume
)
SELECT 
    GenMuzical,
    TO_CHAR(MIN(Luna), 'Mon YYYY') AS PrimaLuna,
    TO_CHAR(MAX(Luna), 'Mon YYYY') AS UltimaLuna,
    MAX(TotalVanzari) AS ValoareMaxima,
    TO_CHAR(
        (SELECT Luna FROM VanzariLunare v2 
         WHERE v2.GenMuzical = v.GenMuzical 
           AND v2.TotalVanzari = MAX(v.TotalVanzari)
         LIMIT 1),
        'Mon YYYY'
    ) AS LunaVarf,
    MIN(TotalVanzari) AS ValoareMinima,
    TO_CHAR(
        (SELECT Luna FROM VanzariLunare v3 
         WHERE v3.GenMuzical = v.GenMuzical 
           AND v3.TotalVanzari = MIN(v.TotalVanzari)
         LIMIT 1),
        'Mon YYYY'
    ) AS LunaCadere
FROM VanzariLunare v
GROUP BY GenMuzical
ORDER BY GenMuzical;


--3. Necesar aprovizionare
WITH PerioadaDate AS (
    SELECT 
        MAX(DataComanda) AS DataMax,
        MAX(DataComanda) - INTERVAL '6 months' AS DataMin
    FROM Comanda
),
VanzariRecente AS (
    SELECT 
        p.TipSuport,
        DATE_TRUNC('month', co.DataComanda) AS Luna,
        SUM(d.Cantitate) AS CantitateLunara
    FROM DetaliuComanda d
    JOIN Produs p ON d.ProdusID = p.ProdusID
    JOIN Comanda co ON d.ComandaID = co.ComandaID
    CROSS JOIN PerioadaDate pd
    WHERE co.DataComanda BETWEEN pd.DataMin AND pd.DataMax
    GROUP BY p.TipSuport, Luna
)
SELECT 
    TipSuport,
    ROUND(AVG(CantitateLunara), 2) AS MedieLunara,
    ROUND(MAX(CantitateLunara), 2) AS VarfLunar,
    ROUND(AVG(CantitateLunara) * 1.15, 0) AS NecesarEstimativ,
    CASE 
        WHEN AVG(CantitateLunara) < 50 THEN 'Aprovizionare scăzută'
        WHEN AVG(CantitateLunara) BETWEEN 50 AND 100 THEN 'Aprovizionare medie'
        ELSE 'Aprovizionare ridicată'
    END AS Recomandare
FROM VanzariRecente
GROUP BY TipSuport
ORDER BY TipSuport;



--4. Vanzari in perioada evenimentelor
SELECT 
    e.Nume AS Eveniment,
    e.DataEveniment,
    SUM(d.Cantitate) AS TotalCantitate,
    SUM(d.TotalLinie) AS TotalVanzari
FROM Eveniment e
JOIN Comanda co ON co.DataComanda BETWEEN e.DataEveniment - INTERVAL '3 days'
                                  AND e.DataEveniment + INTERVAL '3 days'
JOIN DetaliuComanda d ON co.ComandaID = d.ComandaID
GROUP BY e.EvenimentID, e.Nume, e.DataEveniment
ORDER BY e.DataEveniment;

--5. Vanzari estimate cu promotii
SELECT 
    p.Nume AS Produs,
    cat.Nume AS GenMuzical,
    pr.Reducere AS ReducereProcent,
    SUM(d.Cantitate) AS CantitateVanduta,
    ROUND(SUM(d.TotalLinie), 2) AS TotalVanzariActuale,
    ROUND(SUM(d.TotalLinie) * (1 + (pr.Reducere / 100.0) * 0.5), 2) AS TotalVanzariEstimate,
    ROUND(
        (SUM(d.TotalLinie) * (1 + (pr.Reducere / 100.0) * 0.5)) - SUM(d.TotalLinie),
        2
    ) AS CrestereEstimativa
FROM DetaliuComanda d
JOIN Produs p ON d.ProdusID = p.ProdusID
JOIN CategorieProdus cat ON p.CategorieProdusID = cat.CategorieProdusID
JOIN Promotie pr ON p.ProdusID = pr.ProdusID
GROUP BY p.ProdusID, p.Nume, cat.Nume, pr.Reducere
ORDER BY CrestereEstimativa DESC
LIMIT 50;



--6. Top 5 produse cele mai vândute pe fiecare gen muzical
WITH TopProduse AS (
    SELECT
        p.ProdusID,
        p.Nume AS Produs,
        cat.Nume AS GenMuzical,
        SUM(d.Cantitate) AS TotalVandut,
        RANK() OVER(PARTITION BY cat.CategorieProdusID ORDER BY SUM(d.Cantitate) DESC) AS Rang
    FROM DetaliuComanda d
    JOIN Produs p ON d.ProdusID = p.ProdusID
    JOIN CategorieProdus cat ON p.CategorieProdusID = cat.CategorieProdusID
    GROUP BY p.ProdusID, p.Nume, cat.CategorieProdusID, cat.Nume
)
SELECT *
FROM TopProduse
WHERE Rang <= 5
ORDER BY GenMuzical, Rang;

--7. Vânzările medii pe client
SELECT
    c.ClientID,
    INITCAP(c.Prenume || ' ' || c.Nume) AS NumeClient,
    COUNT(DISTINCT co.ComandaID) AS NrComenzi,
    SUM(d.TotalLinie) AS TotalVanzari,
    ROUND(SUM(d.TotalLinie) / COUNT(DISTINCT co.ComandaID), 2) AS VanzareMediePerComanda,
    ROUND(SUM(d.TotalLinie) / SUM(d.Cantitate), 2) AS VanzareMediePerProdus,
    CASE 
        WHEN SUM(d.TotalLinie) > 5000 THEN 'Client Premium'
        WHEN SUM(d.TotalLinie) BETWEEN 2000 AND 5000 THEN 'Client Standard'
        ELSE 'Client Ocazional'
    END AS TipClient
FROM Client c
JOIN Comanda co ON c.ClientID = co.ClientID
JOIN DetaliuComanda d ON co.ComandaID = d.ComandaID
GROUP BY c.ClientID, c.Prenume, c.Nume
ORDER BY TotalVanzari DESC
LIMIT 50;


--8. Clienți fideli: cei care cumpără regulat pe gen muzical
WITH VanzariGenClient AS (
    SELECT
        c.ClientID,
        INITCAP(c.Prenume || ' ' || c.Nume) AS NumeClient,
        cat.Nume AS GenMuzical,
        COUNT(DISTINCT co.ComandaID) AS NrComenzi,
        SUM(d.Cantitate) AS TotalCantitate,
        SUM(d.TotalLinie) AS TotalVanzari
    FROM Client c
    JOIN Comanda co ON c.ClientID = co.ClientID
    JOIN DetaliuComanda d ON co.ComandaID = d.ComandaID
    JOIN Produs p ON d.ProdusID = p.ProdusID
    JOIN CategorieProdus cat ON p.CategorieProdusID = cat.CategorieProdusID
    GROUP BY c.ClientID, c.Prenume, c.Nume, cat.Nume
)
SELECT 
    GenMuzical,
    NumeClient,
    NrComenzi,
    ROUND(TotalVanzari, 2) AS TotalVanzari,
    ROUND(TotalVanzari / NrComenzi, 2) AS MediePerComanda,
    CASE 
        WHEN NrComenzi >= 10 THEN 'Foarte fidel'
        WHEN NrComenzi BETWEEN 5 AND 9 THEN 'Fidel'
        ELSE 'Ocazional'
    END AS NivelFidelitate
FROM VanzariGenClient
WHERE NrComenzi >= 5
ORDER BY GenMuzical, TotalVanzari DESC;

--9. Analiza profitabilității per gen muzical și oraș
WITH ProfitPeGen AS (
    SELECT
        cat.Nume AS GenMuzical,
        c.Oras,
        ROUND(SUM(d.TotalLinie), 2) AS TotalVanzari,
        COUNT(DISTINCT co.ComandaID) AS NrComenzi,
        ROUND(SUM(d.TotalLinie) / COUNT(DISTINCT co.ComandaID), 2) AS MediePerComanda,
        ROUND(SUM(d.TotalLinie) / SUM(d.Cantitate), 2) AS PretMediuProdus
    FROM Client c
    JOIN Comanda co ON c.ClientID = co.ClientID
    JOIN DetaliuComanda d ON co.ComandaID = d.ComandaID
    JOIN Produs p ON d.ProdusID = p.ProdusID
    JOIN CategorieProdus cat ON p.CategorieProdusID = cat.CategorieProdusID
    GROUP BY cat.Nume, c.Oras
)
SELECT 
    GenMuzical,
    Oras,
    TotalVanzari,
    NrComenzi,
    MediePerComanda,
    PretMediuProdus,
    CASE 
        WHEN TotalVanzari > 200000 THEN 'Piață foarte profitabilă'
        WHEN TotalVanzari BETWEEN 100000 AND 200000 THEN 'Piață stabilă'
        ELSE 'Piață de creștere'
    END AS SegmentPiata
FROM ProfitPeGen
ORDER BY GenMuzical, TotalVanzari DESC;



---