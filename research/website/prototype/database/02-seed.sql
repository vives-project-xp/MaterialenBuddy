USE materialenbuddy;

INSERT IGNORE INTO medicijnen (naam, minimum_voorraad)
VALUES
    ('Medicijn A', 5),
    ('Medicijn B', 10);

INSERT INTO voorraad (medicijn_id, aantal)
SELECT id, 20
FROM medicijnen
WHERE naam = 'Medicijn A'
  AND NOT EXISTS (
      SELECT 1 FROM voorraad WHERE medicijn_id = medicijnen.id
  );

INSERT INTO voorraad (medicijn_id, aantal)
SELECT id, 15
FROM medicijnen
WHERE naam = 'Medicijn B'
  AND NOT EXISTS (
      SELECT 1 FROM voorraad WHERE medicijn_id = medicijnen.id
  );
