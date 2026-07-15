from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Dict, Any

import numpy as np
import swisseph as swe
from scipy.optimize import brentq

PLANETS = {
    "Sun": swe.SUN,
    "Moon": swe.MOON,
    "Mercury": swe.MERCURY,
    "Venus": swe.VENUS,
    "Mars": swe.MARS,
    "Jupiter": swe.JUPITER,
    "Saturn": swe.SATURN,
    "Uranus": swe.URANUS,
    "Neptune": swe.NEPTUNE,
    "Pluto": swe.PLUTO,
    "Mean Node": swe.MEAN_NODE,
}

ASPECTS = {
    "Conjunction": 0.0,
    "Sextile": 60.0,
    "Square": 90.0,
    "Trine": 120.0,
    "Opposition": 180.0,
}

PRIMARY_ASPECTS = {
    "Conjunction": 0.0,
    "Semisextile": 30.0,
    "Semisquare": 45.0,
    "Sextile": 60.0,
    "Square": 90.0,
    "Trine": 120.0,
    "Sesquisquare": 135.0,
    "Quincunx": 150.0,
    "Opposition": 180.0,
}

TOPOCENTRIC = b"T"
NAIBOD_DEG_PER_YEAR = (59 + 8.33 / 60) / 60


def normalize(x: float) -> float:
    return x % 360.0


def local_to_utc(dt_local: datetime, utc_offset: float) -> datetime:
    tz = timezone(timedelta(hours=utc_offset))
    return dt_local.replace(tzinfo=tz).astimezone(timezone.utc)


def dt_to_jd(dt: datetime) -> float:
    dt = dt.astimezone(timezone.utc)
    hour = dt.hour + dt.minute / 60 + dt.second / 3600
    return swe.julday(dt.year, dt.month, dt.day, hour, swe.GREG_CAL)


def jd_to_iso(jd: float) -> str:
    y, m, d, h = swe.revjul(jd, swe.GREG_CAL)
    hh = int(h)
    mmf = (h - hh) * 60
    mm = int(mmf)
    ss = min(int(round((mmf - mm) * 60)), 59)
    return datetime(y, m, d, hh, mm, ss, tzinfo=timezone.utc).isoformat()


def angular_distance(a: float, b: float) -> float:
    d = abs((a - b) % 360)
    return min(d, 360 - d)


def planets(jd: float) -> Dict[str, Dict[str, Any]]:
    out = {}
    flags = swe.FLG_SWIEPH | swe.FLG_SPEED
    for name, code in PLANETS.items():
        xx, _ = swe.calc_ut(jd, code, flags)
        out[name] = {
            "longitude": round(normalize(xx[0]), 6),
            "latitude": round(xx[1], 6),
            "speed": round(xx[3], 6),
            "retrograde": xx[3] < 0,
        }
    return out


def houses(jd: float, lat: float, lon: float):
    cusps, ascmc = swe.houses_ex(jd, lat, lon, TOPOCENTRIC, 0)
    return (
        {f"House {i+1}": round(normalize(cusps[i]), 6) for i in range(12)},
        {
            "ASC": round(normalize(ascmc[0]), 6),
            "MC": round(normalize(ascmc[1]), 6),
            "ARMC": round(normalize(ascmc[2]), 6),
            "Vertex": round(normalize(ascmc[3]), 6),
        },
    )


def factors(planets_map, houses_map=None, angles_map=None):
    result = {k: v["longitude"] for k, v in planets_map.items()}
    if houses_map:
        result.update(houses_map)
    if angles_map:
        result.update(angles_map)
    return result


def part_of_fortune(planets_map, angles_map) -> float:
    """Part of Fortune: ASC + Moon - Sun (day/night distinction not applied in this beta)."""
    return normalize(
        float(angles_map["ASC"])
        + float(planets_map["Moon"]["longitude"])
        - float(planets_map["Sun"]["longitude"])
    )


def primary_factor_map(planets_map, houses_map, angles_map):
    """Factors used by the expanded zodiacal Primary Directions beta."""
    result = {name: float(data["longitude"]) for name, data in planets_map.items()}
    result.update({name: float(lon) for name, lon in houses_map.items()})
    result.update({
        "ASC": float(angles_map["ASC"]),
        "MC": float(angles_map["MC"]),
    })
    result["Part of Fortune"] = part_of_fortune(planets_map, angles_map)
    return result


def primary_orb_limit_arcmin(aspect_name: str) -> float:
    # Book-inspired limits used in this beta:
    # conjunction/opposition up to 11', other aspects up to 6'.
    return 11.0 if aspect_name in ("Conjunction", "Opposition") else 6.0


def signed_aspect_residual(separation: float, exact_angle: float) -> float:
    """Signed residual in degrees around an exact aspect."""
    return separation - exact_angle


def primary_directions_zodiacal_beta(
    natal_jd: float,
    target_jd: float,
    lat: float,
    lon: float,
    natal_planets: Dict[str, Dict[str, Any]],
    natal_houses: Dict[str, float],
    natal_angles: Dict[str, float],
):
    """
    Expanded zodiacal Primary Directions beta.

    Supports:
    - Direct and converse directions
    - Planets, Mean Node, ASC, MC, all house cusps, Part of Fortune
    - Major and minor aspects listed in the book
    - Naibod key
    - Tight arc-minute orbs

    Important: this is an ecliptic/Naibod beta. It is NOT yet the full
    topocentric speculum (OA/OD, poles, semi-arcs and mundane directions).
    """
    age_years = (target_jd - natal_jd) / 365.2422
    arc = age_years * NAIBOD_DEG_PER_YEAR
    natal_factors = primary_factor_map(natal_planets, natal_houses, natal_angles)
    rows = []

    # House/angle positions are re-derived from a synthetic sidereal rotation;
    # planets and points are shifted by the Naibod arc in zodiacal longitude.
    for direction, sign in (("Direct", 1), ("Converse", -1)):
        synthetic_jd = natal_jd + sign * arc / 360.98564736629
        directed_houses, directed_angles = houses(synthetic_jd, lat, lon)

        directed_factors = {}
        for name, natal_lon in natal_factors.items():
            if name.startswith("House "):
                directed_factors[name] = float(directed_houses[name])
            elif name in ("ASC", "MC"):
                directed_factors[name] = float(directed_angles[name])
            else:
                directed_factors[name] = normalize(float(natal_lon) + sign * arc)

        for directed_name, directed_lon in directed_factors.items():
            for radical_name, radical_lon in natal_factors.items():
                # Avoid self-conjunction artifacts for the same factor.
                if directed_name == radical_name:
                    continue

                sep = angular_distance(directed_lon, radical_lon)
                for aspect_name, exact_angle in PRIMARY_ASPECTS.items():
                    orb_deg = abs(sep - exact_angle)
                    orb_arcmin = orb_deg * 60.0
                    limit = primary_orb_limit_arcmin(aspect_name)
                    if orb_arcmin <= limit:
                        # Approximate temporal distance from exactitude:
                        # 1 arc minute ≈ 365.2422 / (Naibod arcminutes/year) days.
                        naibod_arcmin_year = NAIBOD_DEG_PER_YEAR * 60.0
                        days_per_arcmin = 365.2422 / naibod_arcmin_year
                        time_window_days = orb_arcmin * days_per_arcmin

                        rows.append({
                            "direction": direction,
                            "significator": directed_name,
                            "aspect": aspect_name,
                            "natal_factor": radical_name,
                            "orb_arcmin": round(orb_arcmin, 3),
                            "orb_limit_arcmin": limit,
                            "time_window_days": round(time_window_days, 1),
                            "naibod_arc_deg": round(arc, 6),
                            "directed_longitude": round(normalize(directed_lon), 6),
                            "radical_longitude": round(normalize(radical_lon), 6),
                            "method": "Expanded zodiacal beta (Naibod)",
                        })
                        break

    return sorted(
        rows,
        key=lambda x: (
            x["orb_arcmin"],
            0 if x["significator"] in ("ASC", "MC") or x["natal_factor"] in ("ASC", "MC") else 1,
        ),
    )


def aspect_rows(moving, natal, max_orb=2.0):
    rows = []
    for m_name, m_lon in moving.items():
        for n_name, n_lon in natal.items():
            sep = angular_distance(m_lon, n_lon)
            for asp_name, asp_deg in ASPECTS.items():
                orb = abs(sep - asp_deg)
                if orb <= max_orb:
                    rows.append({
                        "moving_factor": m_name,
                        "aspect": asp_name,
                        "natal_factor": n_name,
                        "orb": round(orb, 4),
                        "separation": round(sep, 4),
                    })
    return sorted(rows, key=lambda x: x["orb"])


def sun_lon(jd: float) -> float:
    xx, _ = swe.calc_ut(jd, swe.SUN, swe.FLG_SWIEPH)
    return normalize(xx[0])


def signed_diff(a: float, b: float) -> float:
    return ((a - b + 180) % 360) - 180


def solar_return_jd(natal_jd: float, year: int) -> float:
    natal_sun = sun_lon(natal_jd)
    y, m, d, _ = swe.revjul(natal_jd, swe.GREG_CAL)
    guess = dt_to_jd(datetime(year, m, d, 12, tzinfo=timezone.utc))

    def f(jd):
        return signed_diff(sun_lon(jd), natal_sun)

    xs = np.linspace(guess - 3, guess + 3, 145)
    vals = [f(x) for x in xs]
    for a, b, fa, fb in zip(xs[:-1], xs[1:], vals[:-1], vals[1:]):
        if abs(fa - fb) < 30 and fa * fb <= 0:
            return brentq(f, a, b, xtol=1e-10)
    raise ValueError("تعذر تحديد العودة الشمسية. راجع البيانات.")


def secondary_progressed_jd(natal_jd: float, target_jd: float) -> float:
    age_years = (target_jd - natal_jd) / 365.2422
    return natal_jd + age_years


def primary_directions_asc_mc(natal_jd, target_jd, lat, lon, natal_factors, max_orb_arcmin=11.0):
    age_years = (target_jd - natal_jd) / 365.2422
    arc = age_years * NAIBOD_DEG_PER_YEAR
    _, natal_angles = houses(natal_jd, lat, lon)
    natal_armc = natal_angles["ARMC"]
    rows = []

    for direction, sign in (("Direct", 1), ("Converse", -1)):
        synthetic_jd = natal_jd + sign * arc / 360.98564736629
        _, directed_angles = houses(synthetic_jd, lat, lon)
        for sig in ("ASC", "MC"):
            sig_lon = directed_angles[sig]
            for natal_name, natal_lon in natal_factors.items():
                if natal_name.startswith("House "):
                    continue
                sep = angular_distance(sig_lon, natal_lon)
                for asp_name, asp_deg in ASPECTS.items():
                    orb_arcmin = abs(sep - asp_deg) * 60
                    if orb_arcmin <= max_orb_arcmin:
                        rows.append({
                            "direction": direction,
                            "significator": sig,
                            "aspect": asp_name,
                            "natal_factor": natal_name,
                            "orb_arcmin": round(orb_arcmin, 3),
                            "naibod_arc_deg": round(arc, 6),
                            "directed_armc": round(normalize(natal_armc + sign * arc), 6),
                        })
    return sorted(rows, key=lambda x: x["orb_arcmin"])


def calculate(payload: Dict[str, Any]) -> Dict[str, Any]:
    birth_local = datetime.fromisoformat(payload["birth_datetime"])
    event_local = datetime.fromisoformat(payload["event_datetime"])

    birth_utc = local_to_utc(birth_local, float(payload["birth_utc_offset"]))
    event_utc = local_to_utc(event_local, float(payload["event_utc_offset"]))

    natal_jd = dt_to_jd(birth_utc)
    event_jd = dt_to_jd(event_utc)

    n_planets = planets(natal_jd)
    n_houses, n_angles = houses(natal_jd, payload["birth_lat"], payload["birth_lon"])
    n_factors = factors(n_planets, n_houses, n_angles)

    t_planets = planets(event_jd)
    _, t_angles = houses(event_jd, payload["event_lat"], payload["event_lon"])
    t_factors = factors(t_planets, None, t_angles)

    sr_jd = solar_return_jd(natal_jd, event_utc.year)
    sr_planets = planets(sr_jd)
    sr_houses, sr_angles = houses(sr_jd, payload["solar_return_lat"], payload["solar_return_lon"])
    sr_factors = factors(sr_planets, sr_houses, sr_angles)

    prog_jd = secondary_progressed_jd(natal_jd, event_jd)
    prog_planets = planets(prog_jd)
    prog_houses, prog_angles = houses(prog_jd, payload["birth_lat"], payload["birth_lon"])
    prog_factors = factors(prog_planets, prog_houses, prog_angles)

    max_orb = float(payload.get("max_orb", 2.0))

    return {
        "metadata": {
            "name": payload.get("name", ""),
            "birth_utc": birth_utc.isoformat(),
            "event_utc": event_utc.isoformat(),
            "solar_return_utc": jd_to_iso(sr_jd),
            "progressed_utc": jd_to_iso(prog_jd),
            "house_system": "Topocentric (Polich/Page)",
            "primary_directions_scope": "Expanded zodiacal beta: planets, houses, ASC/MC, Part of Fortune; Direct+Converse; Naibod",
        },
        "natal": {"planets": n_planets, "houses": n_houses, "angles": n_angles},
        "transits": {
            "planets": t_planets,
            "angles": t_angles,
            "aspects_to_natal": aspect_rows(t_factors, n_factors, max_orb),
        },
        "solar_return": {
            "planets": sr_planets,
            "houses": sr_houses,
            "angles": sr_angles,
            "aspects_to_natal": aspect_rows(sr_factors, n_factors, max_orb),
        },
        "secondary_progressions": {
            "planets": prog_planets,
            "houses": prog_houses,
            "angles": prog_angles,
            "aspects_to_natal": aspect_rows(prog_factors, n_factors, max_orb),
        },
        "primary_directions_experimental": primary_directions_zodiacal_beta(
            natal_jd=natal_jd,
            target_jd=event_jd,
            lat=payload["birth_lat"],
            lon=payload["birth_lon"],
            natal_planets=n_planets,
            natal_houses=n_houses,
            natal_angles=n_angles,
        ),
    }
