"""Household flood GUL, insurance payout, and out-of-pocket loss.

Values use the existing damage model's units (2418/880/320): 万円, or
10,000 Japanese yen per unit. GUL, payout and OOP retain that unit.
The selected research assumption covers building, contents AND vehicle loss
in full when the household is insured at flood impact. An uninsured household
bears all three losses. No deductible, exclusion or payout limit is applied.
"""

from __future__ import annotations


BUILDING_VALUE = 2418.0
CONTENTS_VALUE = 880.0
VEHICLE_VALUE = 320.0
LOSS_POLICY = "full_all_assets_v1"


def reset_annual_losses(households) -> None:
    """Prevent a past flood loss from carrying into a no-flood year."""
    for hh in households:
        hh.loss_mesh_id = hh.mesh_id
        hh.flood_depth_m = 0.0
        hh.insured_at_flood = False
        for part in ("building", "contents", "vehicle"):
            setattr(hh, f"{part}_damage_ratio", 0.0)
            setattr(hh, f"{part}_gul", 0.0)
            setattr(hh, f"{part}_payout", 0.0)
            setattr(hh, f"{part}_oop", 0.0)
        hh.gul = 0.0
        hh.insurance_payout = 0.0
        hh.oop = 0.0


def record_flood_loss(hh, depth_m: float, damage: dict[str, float]) -> None:
    """Record one household's event loss using coverage in force at impact."""
    hh.loss_mesh_id = hh.mesh_id  # Preserve exposure zone before relocation.
    hh.flood_depth_m = float(depth_m)
    hh.insured_at_flood = bool(hh.insured)
    for part, ratio_key, default_value in (
        ("building", "house_damage_ratio", BUILDING_VALUE),
        ("contents", "content_damage_ratio", CONTENTS_VALUE),
        ("vehicle", "vehicle_damage_ratio", VEHICLE_VALUE),
    ):
        ratio = float(damage[ratio_key])
        if not 0.0 <= ratio <= 1.0:
            raise ValueError(f"Invalid {part} damage ratio: {ratio}")
        value = float(getattr(hh, f"{part}_value", default_value))
        if value < 0:
            raise ValueError(f"Invalid {part} value: {value}")
        gul = value * ratio
        payout = gul if hh.insured_at_flood else 0.0
        setattr(hh, f"{part}_damage_ratio", ratio)
        setattr(hh, f"{part}_gul", gul)
        setattr(hh, f"{part}_payout", payout)
        setattr(hh, f"{part}_oop", gul - payout)
    hh.gul = hh.building_gul + hh.contents_gul + hh.vehicle_gul
    hh.insurance_payout = hh.building_payout + hh.contents_payout + hh.vehicle_payout
    hh.oop = hh.gul - hh.insurance_payout
