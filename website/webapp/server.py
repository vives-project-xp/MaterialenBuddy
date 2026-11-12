import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, text

import auth


BASE_DIR = Path(__file__).parent
load_dotenv(BASE_DIR / ".env", override=True)
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL ontbreekt. Maak een .env-bestand aan.")

engine = create_engine(DATABASE_URL, pool_pre_ping=True)


def _ensure_schema() -> None:
    """Brengt het schema up-to-date voor bestaande databases.

    Draait idempotent bij elke opstart, zodat een lopende installatie (waar de
    initdb-scripts niet opnieuw draaien) ook nieuwe kolommen krijgt.
    """
    with engine.connect() as connection:
        kolommen = connection.execute(
            text(
                "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS "
                "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'medicijnen'"
            )
        ).mappings().all()
        namen = {row["COLUMN_NAME"] for row in kolommen}
        if "actief" not in namen:
            connection.execute(
                text(
                    "ALTER TABLE medicijnen "
                    "ADD COLUMN actief BOOLEAN NOT NULL DEFAULT TRUE"
                )
            )
            connection.commit()


_ensure_schema()

app = FastAPI(title="MaterialenBuddy voorraad API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

app.include_router(auth.router)


class LeveringMedicijn(BaseModel):
    naam: str = Field(min_length=1)
    aantal: int = Field(gt=0)


class LeveringAanvraag(BaseModel):
    startlocatie: str = Field(min_length=1)
    bestemming: str = Field(min_length=1)
    medicijnen: list[LeveringMedicijn] = Field(min_length=1)


class VoorraadAanvulling(BaseModel):
    aantal: int = Field(gt=0)


class NieuwMedicijn(BaseModel):
    naam: str = Field(min_length=1, max_length=150)
    minimum_voorraad: int = Field(ge=0, default=0)
    voorraad: int = Field(ge=0, default=0)


@app.get("/", include_in_schema=False)
async def index() -> FileResponse:
    return FileResponse(
        BASE_DIR / "index.html",
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )


@app.get("/medicijnen")
def medicijnen(
    sessie: dict[str, Any] = Depends(auth.require_auth),
) -> list[dict[str, Any]]:
    with engine.connect() as connection:
        rows = connection.execute(
            text("""
                SELECT m.id, m.naam, m.minimum_voorraad,
                       COALESCE(v.aantal, 0) AS aantal
                FROM medicijnen m
                LEFT JOIN voorraad v ON v.medicijn_id = m.id
                WHERE m.actief = TRUE
                ORDER BY m.naam
            """)
        ).mappings()
        return [dict(row) for row in rows]


@app.get("/voorraad")
def voorraad(
    sessie: dict[str, Any] = Depends(auth.require_auth),
) -> list[dict[str, Any]]:
    return medicijnen(sessie=sessie)


@app.post("/voorraad/{medicijn_id}")
def voorraad_aanvullen(
    medicijn_id: int,
    aanvulling: VoorraadAanvulling,
    sessie: dict[str, Any] = Depends(auth.require_staff),
) -> dict[str, Any]:
    with engine.begin() as connection:
        medicijn = connection.execute(
            text("SELECT id FROM medicijnen WHERE id = :id"),
            {"id": medicijn_id},
        ).mappings().first()
        if medicijn is None:
            raise HTTPException(status_code=404, detail="Medicijn niet gevonden")

        bestaande_voorraad = connection.execute(
            text("SELECT id FROM voorraad WHERE medicijn_id = :medicijn_id"),
            {"medicijn_id": medicijn_id},
        ).mappings().first()

        if bestaande_voorraad is None:
            connection.execute(
                text("""
                    INSERT INTO voorraad (medicijn_id, aantal)
                    VALUES (:medicijn_id, :aantal)
                """),
                {"medicijn_id": medicijn_id, "aantal": aanvulling.aantal},
            )
        else:
            connection.execute(
                text("""
                    UPDATE voorraad
                    SET aantal = aantal + :aantal
                    WHERE medicijn_id = :medicijn_id
                """),
                {"medicijn_id": medicijn_id, "aantal": aanvulling.aantal},
            )

        connection.execute(
            text("""
                INSERT INTO voorraad_mutaties
                    (medicijn_id, verschil, reden)
                VALUES (:medicijn_id, :verschil, :reden)
            """),
            {
                "medicijn_id": medicijn_id,
                "verschil": aanvulling.aantal,
                "reden": "Handmatig aangevuld",
            },
        )

    return {"medicijn_id": medicijn_id, "toegevoegd": aanvulling.aantal}


@app.post("/medicijnen", status_code=201)
def medicijn_toevoegen(
    medicijn: NieuwMedicijn,
    sessie: dict[str, Any] = Depends(auth.require_staff),
) -> dict[str, Any]:
    """Voegt een nieuw voorraadproduct toe (staff-only)."""
    with engine.begin() as connection:
        resultaat = connection.execute(
            text(
                """
                INSERT INTO medicijnen (naam, minimum_voorraad, actief)
                VALUES (:naam, :minimum_voorraad, TRUE)
                """
            ),
            {
                "naam": medicijn.naam.strip(),
                "minimum_voorraad": medicijn.minimum_voorraad,
            },
        )
        medicijn_id = resultaat.lastrowid

        if medicijn.voorraad > 0:
            connection.execute(
                text(
                    """
                    INSERT INTO voorraad (medicijn_id, aantal)
                    VALUES (:medicijn_id, :aantal)
                    """
                ),
                {"medicijn_id": medicijn_id, "aantal": medicijn.voorraad},
            )
            connection.execute(
                text(
                    """
                    INSERT INTO voorraad_mutaties
                        (medicijn_id, verschil, reden)
                    VALUES (:medicijn_id, :verschil, :reden)
                    """
                ),
                {
                    "medicijn_id": medicijn_id,
                    "verschil": medicijn.voorraad,
                    "reden": "Voorraad geïnitieerd bij aanmaak",
                },
            )

    return {
        "naam": medicijn.naam.strip(),
        "minimum_voorraad": medicijn.minimum_voorraad,
        "voorraad": medicijn.voorraad,
    }


@app.delete("/medicijnen/{medicijn_id}")
def medicijn_uitfaseren(
    medicijn_id: int,
    sessie: dict[str, Any] = Depends(auth.require_staff),
) -> dict[str, Any]:
    """Faseert een product uit: verdwijnt uit de voorraad, historiek blijft intact.

    We markeren het product inactief in plaats van het te wissen, zodat de
    audit-tables (voorraad_mutaties, leveringen) hun referentie behouden.
    """
    with engine.begin() as connection:
        resultaat = connection.execute(
            text("UPDATE medicijnen SET actief = FALSE WHERE id = :id"),
            {"id": medicijn_id},
        )
        if resultaat.rowcount == 0:
            raise HTTPException(status_code=404, detail="Medicijn niet gevonden")
    return {"medicijn_id": medicijn_id, "actief": False}


@app.get("/medicijnen/uitgefaseerd")
def medicijnen_uitgefaseerd(
    sessie: dict[str, Any] = Depends(auth.require_staff),
) -> list[dict[str, Any]]:
    """Lijst de uitgefaseerde (inactieve) producten op (staff-only)."""
    with engine.connect() as connection:
        rows = connection.execute(
            text("""
                SELECT m.id, m.naam
                FROM medicijnen m
                WHERE m.actief = FALSE
                ORDER BY m.naam
            """)
        ).mappings()
        return [dict(row) for row in rows]


@app.post("/leveringen", status_code=201)
def levering_aanmaken(
    aanvraag: LeveringAanvraag,
    sessie: dict[str, Any] = Depends(auth.require_auth),
) -> dict[str, Any]:
    with engine.begin() as connection:
        levering = connection.execute(
            text("""
                INSERT INTO leveringen (startlocatie, bestemming, status)
                VALUES (:startlocatie, :bestemming, 'aangevraagd')
            """),
            aanvraag.model_dump(exclude={"medicijnen"}),
        )
        levering_id = levering.lastrowid

        for medicijn in aanvraag.medicijnen:
            voorraad = connection.execute(
                text("""
                    SELECT m.id, COALESCE(v.aantal, 0) AS aantal
                    FROM medicijnen m
                    LEFT JOIN voorraad v ON v.medicijn_id = m.id
                    WHERE LOWER(m.naam) = LOWER(:naam)
                    FOR UPDATE
                """),
                {"naam": medicijn.naam},
            ).mappings().first()

            if voorraad is None:
                raise HTTPException(
                    status_code=404,
                    detail=f"Medicijn niet gevonden: {medicijn.naam}",
                )
            if voorraad["aantal"] < medicijn.aantal:
                raise HTTPException(
                    status_code=409,
                    detail=f"Onvoldoende voorraad voor: {medicijn.naam}",
                )

            connection.execute(
                text("""
                    INSERT INTO levering_medicijnen
                        (levering_id, medicijn_id, aantal)
                    VALUES (:levering_id, :medicijn_id, :aantal)
                """),
                {
                    "levering_id": levering_id,
                    "medicijn_id": voorraad["id"],
                    "aantal": medicijn.aantal,
                },
            )
            connection.execute(
                text("""
                    UPDATE voorraad
                    SET aantal = aantal - :aantal
                    WHERE medicijn_id = :medicijn_id
                """),
                {"aantal": medicijn.aantal, "medicijn_id": voorraad["id"]},
            )
            connection.execute(
                text("""
                    INSERT INTO voorraad_mutaties
                        (medicijn_id, levering_id, verschil, reden)
                    VALUES (:medicijn_id, :levering_id, :verschil, :reden)
                """),
                {
                    "medicijn_id": voorraad["id"],
                    "levering_id": levering_id,
                    "verschil": -medicijn.aantal,
                    "reden": "Levering aangevraagd",
                },
            )

        return {"id": levering_id, "status": "aangevraagd"}


@app.get("/leveringen/{levering_id}")
def levering_ophalen(
    levering_id: int,
    sessie: dict[str, Any] = Depends(auth.require_auth),
) -> dict[str, Any]:
    with engine.connect() as connection:
        row = connection.execute(
            text("""
                SELECT id, startlocatie, bestemming, status,
                       aangemaakt_op, voltooid_op
                FROM leveringen
                WHERE id = :id
            """),
            {"id": levering_id},
        ).mappings().first()
        if row is None:
            raise HTTPException(status_code=404, detail="Levering niet gevonden")
        return dict(row)