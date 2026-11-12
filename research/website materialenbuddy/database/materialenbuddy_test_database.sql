CREATE DATABASE IF NOT EXISTS materialenbuddy
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE materialenbuddy;

CREATE TABLE medicijnen (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    naam VARCHAR(150) NOT NULL UNIQUE,
    minimum_voorraad INT UNSIGNED NOT NULL DEFAULT 0,
    aangemaakt_op TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE TABLE voorraad (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    medicijn_id INT UNSIGNED NOT NULL UNIQUE,
    aantal INT NOT NULL DEFAULT 0,
    bijgewerkt_op TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,

    CONSTRAINT chk_voorraad_aantal
        CHECK (aantal >= 0),

    CONSTRAINT fk_voorraad_medicijn
        FOREIGN KEY (medicijn_id)
        REFERENCES medicijnen(id)
        ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE leveringen (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    startlocatie VARCHAR(100) NOT NULL,
    bestemming VARCHAR(100) NOT NULL,
    status ENUM(
        'aangevraagd',
        'onderweg',
        'aangekomen',
        'geannuleerd',
        'fout'
    ) NOT NULL DEFAULT 'aangevraagd',
    aangemaakt_op TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    voltooid_op TIMESTAMP NULL
) ENGINE=InnoDB;

CREATE TABLE levering_medicijnen (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    levering_id INT UNSIGNED NOT NULL,
    medicijn_id INT UNSIGNED NOT NULL,
    aantal INT UNSIGNED NOT NULL,

    CONSTRAINT chk_levering_aantal
        CHECK (aantal > 0),

    CONSTRAINT fk_levering_medicijnen_levering
        FOREIGN KEY (levering_id)
        REFERENCES leveringen(id)
        ON DELETE CASCADE,

    CONSTRAINT fk_levering_medicijnen_medicijn
        FOREIGN KEY (medicijn_id)
        REFERENCES medicijnen(id)
        ON DELETE RESTRICT
) ENGINE=InnoDB;

CREATE TABLE voorraad_mutaties (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    medicijn_id INT UNSIGNED NOT NULL,
    levering_id INT UNSIGNED NULL,
    verschil INT NOT NULL,
    reden VARCHAR(255) NOT NULL,
    aangemaakt_op TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_mutaties_medicijn
        FOREIGN KEY (medicijn_id)
        REFERENCES medicijnen(id)
        ON DELETE RESTRICT,

    CONSTRAINT fk_mutaties_levering
        FOREIGN KEY (levering_id)
        REFERENCES leveringen(id)
        ON DELETE SET NULL
) ENGINE=InnoDB;