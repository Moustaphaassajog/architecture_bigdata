from pydantic import BaseModel
from typing import Optional


class EntrepriseSearchResult(BaseModel):
    enterprise_number: str
    denomination: Optional[str] = None
    status_label: Optional[str] = None
    juridical_form_label: Optional[str] = None


class RatiosYear(BaseModel):
    year: int
    ca: float
    marge_brute: float
    ebit: float
    resultat_net: float
    tresorerie: float
    dettes_financieres: float
    fonds_propres: float
    capital_souscrit: float
    ratios: dict


class FicheEntreprise(BaseModel):
    enterprise_number: str
    denomination: Optional[str] = None
    juridical_form_label: Optional[str] = None
    status_label: Optional[str] = None
    start_date: Optional[str] = None
    address: Optional[dict] = None
    activities: list = []
    years: list = []