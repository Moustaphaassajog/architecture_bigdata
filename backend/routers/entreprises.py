from fastapi import APIRouter, HTTPException, Query
from backend.database import silver_coll, gold_coll

router = APIRouter(prefix="/entreprises", tags=["entreprises"])


def _clean_bce(bce: str) -> str:
    return bce.replace(".", "").strip()


@router.get("/search")
def search_entreprises(q: str = Query(..., min_length=2)):
    """Recherche par numero BCE ou nom d'entreprise."""
    q_clean = _clean_bce(q)

    # Recherche par BCE (avec ou sans points)
    results = list(silver_coll.find(
        {"EnterpriseNumber": {"$regex": q_clean}},
        {"EnterpriseNumber": 1, "denominations": 1, "StatusLabel": 1, "JuridicalFormLabel": 1, "_id": 0}
    ).limit(20))

    # Si peu de résultats, recherche aussi par nom
    if len(results) < 5:
        name_results = list(silver_coll.find(
            {"denominations.Denomination": {"$regex": q, "$options": "i"}},
            {"EnterpriseNumber": 1, "denominations": 1, "StatusLabel": 1, "JuridicalFormLabel": 1, "_id": 0}
        ).limit(20))
        seen = {r["EnterpriseNumber"] for r in results}
        results.extend([r for r in name_results if r["EnterpriseNumber"] not in seen])

    output = []
    for r in results:
        denom = r.get("denominations", [{}])[0].get("Denomination") if r.get("denominations") else None
        output.append({
            "enterprise_number": r["EnterpriseNumber"],
            "denomination": denom,
            "status_label": r.get("StatusLabel"),
            "juridical_form_label": r.get("JuridicalFormLabel"),
        })

    return output


@router.get("/{bce}")
def get_fiche_entreprise(bce: str):
    """Fiche complete : infos Silver + ratios Gold."""
    bce_dotted_variants = [bce, _clean_bce(bce)]

    silver_doc = silver_coll.find_one({"EnterpriseNumber": {"$in": bce_dotted_variants}})
    if not silver_doc:
        raise HTTPException(status_code=404, detail="Entreprise non trouvee dans enterprise_silver")

    bce_clean = _clean_bce(silver_doc["EnterpriseNumber"])
    gold_doc = gold_coll.find_one({"enterprise_number": bce_clean})

    denom = None
    if silver_doc.get("denominations"):
        denom = silver_doc["denominations"][0].get("Denomination")

    address = None
    if silver_doc.get("addresses"):
        address = silver_doc["addresses"][0]
        address.pop("_id", None)

    activities = []
    for act in silver_doc.get("activities", []):
        activities.append({
            "nace_code": act.get("NaceCode"),
            "nace_version": act.get("NaceVersion"),
            "classification": act.get("Classification"),
            "label": act.get("NaceLabel"),
        })

    return {
        "enterprise_number": silver_doc["EnterpriseNumber"],
        "denomination": denom,
        "juridical_form_label": silver_doc.get("JuridicalFormLabel"),
        "status_label": silver_doc.get("StatusLabel"),
        "start_date": silver_doc.get("StartDate"),
        "address": address,
        "activities": activities,
        "years": gold_doc.get("years", []) if gold_doc else [],
        "schema_type": gold_doc.get("schema_type") if gold_doc else None,
    }