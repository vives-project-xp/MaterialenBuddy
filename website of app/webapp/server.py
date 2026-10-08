import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, text


BASE_DIR = Path(__file__).parent
load_dotenv(BASE_DIR / ".env")
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL ontbreekt. Maak een .env-bestand aan.")

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
app = FastAPI(title="MaterialenBuddy voorraad API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class LeveringMedicijn(BaseModel):
    naam: str = Field(min_length=1)
    aantal: int = Field(gt=0)


class LeveringAanvraag(BaseModel):
    startlocatie: str = Field(min_length=1)
    bestemming: str = Field(min_length=1)
    medicijnen: list[LeveringMedicijn] = Field(min_length=1)


@app.get("/", include_in_schema=False)
async def index() -> FileResponse:
    return FileResponse(BASE_DIR / "index.html")


@app.get("/medicijnen")
def medicijnen() -> list[dict[str, Any]]:
    with engine.connect() as connection:
        rows = connection.execute(
            text("""
                SELECT m.id, m.naam, m.minimum_voorraad,
                       COALESCE(v.aantal, 0) AS aantal
                FROM medicijnen m
                LEFT JOIN voorraad v ON v.medicijn_id = m.id
                ORDER BY m.naam
            """)
        ).mappings()
        return [dict(row) for row in rows]


@app.get("/voorraad")
def voorraad() -> list[dict[str, Any]]:
    return medicijnen()


@app.post("/leveringen", status_code=201)
def levering_aanmaken(aanvraag: LeveringAanvraag) -> dict[str, Any]:
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
def levering_ophalen(levering_id: int) -> dict[str, Any]:
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