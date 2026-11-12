/*hoevel er in vooraad is*/
USE materialenbuddy;
SELECT
    medicijnen.naam,
    voorraad.aantal,
    medicijnen.minimum_voorraad
FROM medicijnen
LEFT JOIN voorraad
    ON voorraad.medicijn_id = medicijnen.id;