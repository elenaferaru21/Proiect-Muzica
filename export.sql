COPY (
    SELECT 
        ClientID,
        Prenume,
        Nume,
        DataNasterii,
        EXTRACT(YEAR FROM AGE(CURRENT_DATE, DataNasterii)) AS Varsta,
        NivelStudii,
        Oras
    FROM Client
) TO 'C:\PowerPivot_Export\Client.csv'
WITH (FORMAT CSV, HEADER, DELIMITER ',', ENCODING 'UTF8');


COPY (
    SELECT 
        ProdusID,
        Nume AS NumeProdus,
        CategorieProdusID,
        TipSuport,
        Pret
    FROM Produs
) TO 'C:\PowerPivot_Export\Produs.csv'
WITH (FORMAT CSV, HEADER, DELIMITER ',', ENCODING 'UTF8');



COPY (
    SELECT 
        ProdusID,
        Nume AS NumeProdus,
        CategorieProdusID,
        TipSuport,
        Pret
    FROM Produs
) TO 'C:\PowerPivot_Export\Produs.csv'
WITH (FORMAT CSV, HEADER, DELIMITER ',', ENCODING 'UTF8');



COPY (
    SELECT 
        ComandaID,
        ClientID,
        DataComanda,
        EXTRACT(YEAR FROM DataComanda) AS An,
        EXTRACT(QUARTER FROM DataComanda) AS Trimestru,
        EXTRACT(MONTH FROM DataComanda) AS Luna,
        EXTRACT(DAY FROM DataComanda) AS Zi,
        Total
    FROM Comanda
    WHERE EXTRACT(YEAR FROM DataComanda) = 2023
) TO 'C:\PowerPivot_Export\Comanda.csv'
WITH (FORMAT CSV, HEADER, DELIMITER ',', ENCODING 'UTF8');


COPY (
    SELECT 
        DetaliuComandaID,
        ComandaID,
        ProdusID,
        Cantitate,
        TotalLinie
    FROM DetaliuComanda
) TO 'C:\PowerPivot_Export\DetaliuComanda.csv'
WITH (FORMAT CSV, HEADER, DELIMITER ',', ENCODING 'UTF8');


COPY (
    SELECT 
        EvenimentID,
        Nume AS NumeEveniment,
        DataEveniment
    FROM Eveniment
    WHERE EXTRACT(YEAR FROM DataEveniment) = 2023
) TO 'C:\PowerPivot_Export\Eveniment.csv'
WITH (FORMAT CSV, HEADER, DELIMITER ',', ENCODING 'UTF8');



COPY (
    SELECT 
        PromotieID,
        ProdusID,
        Reducere,
        DataStart,
        DataEnd
    FROM Promotie
    WHERE EXTRACT(YEAR FROM DataStart) = 2023
) TO 'C:\PowerPivot_Export\Promotie.csv'
WITH (FORMAT CSV, HEADER, DELIMITER ',', ENCODING 'UTF8');
