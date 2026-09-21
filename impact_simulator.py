from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

BASE = Path(__file__).resolve().parent
DATA_DIR = BASE / "data"
BASELINE_PATH = DATA_DIR / "impact_baseline.json"
MEASURES_PATH = DATA_DIR / "impact_measures.json"

NAVY = "#032F67"
GREEN = "#16855B"
GREEN_BG = "#EAF7F1"
RED = "#C33B3B"
MUTED = "#667085"
BORDER = "#E3E8EF"
ORANGE = "#B7791F"

# Année 1 (80 Md€) et Année 5 (200 Md€) sont les deux repères publiés utilisés par le module.
# Les années 2 à 4 sont une interpolation LINEAIRE, explicitement signalée comme hypothèse de visualisation.
PHASE_RATIOS = {
    "Année 1": 0.40,
    "Année 2": 0.55,
    "Année 3": 0.70,
    "Année 4": 0.85,
    "Année 5": 1.00,
    # Compatibilité avec les anciennes versions / tests.
    "Trajectoire cible": 1.00,
}
PHASE_LABELS = ["Année 1", "Année 2", "Année 3", "Année 4", "Année 5"]


def _phase_ratio(phase: str) -> float:
    return float(PHASE_RATIOS.get(phase, 1.0))


def _phase_is_estimated(phase: str) -> bool:
    return phase in {"Année 2", "Année 3", "Année 4"}


def _phase_number(phase: str) -> int:
    if phase == "Trajectoire cible":
        return 5
    try:
        return int(phase.rsplit(" ", 1)[-1])
    except Exception:
        return 5


def _load_json(path: Path, fallback: Any):
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return fallback


def fmt_bn(value: float | None, signed: bool = False) -> str:
    if value is None:
        return "—"
    sign = "+" if signed and value > 0 else ""
    txt = f"{sign}{value:,.1f} Md€".replace(",", " ")
    return txt.replace(".0 Md€", " Md€")


def fmt_eur(value: float | None, signed: bool = False) -> str:
    if value is None:
        return "—"
    sign = "+" if signed and value > 0 else ""
    return f"{sign}{value:,.0f} €".replace(",", " ")


def fmt_pct(value: float | None, digits: int = 1, signed: bool = False) -> str:
    if value is None:
        return "—"
    sign = "+" if signed and value > 0 else ""
    return f"{sign}{value:.{digits}f} %".replace(".", ",")


def _inject_css():
    st.markdown(
        """
<style>
.impact-intro {margin-bottom:.35rem;color:#667085;font-size:.94rem;}
.impact-grid {display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;margin:.35rem 0 .65rem 0;}
.impact-card {border:1px solid #E3E8EF;border-radius:15px;padding:12px 15px;background:#fff;min-height:82px;}
.impact-card .k {font-size:.78rem;color:#667085;margin-bottom:3px;line-height:1.25;}
.impact-card .v {font-size:1.48rem;font-weight:800;color:#032F67;line-height:1.15;letter-spacing:-.02em;}
.impact-card.good .v {color:#16855B;}
.impact-card.bad .v {color:#B42318;}
.impact-card .d {display:inline-block;margin-top:5px;padding:2px 7px;border-radius:999px;font-size:.73rem;font-weight:700;background:#F2F4F7;color:#667085;}
.impact-card .d.good {background:#EAF7F1;color:#16855B;}
.impact-card .d.warn {background:#FFF6E8;color:#9A6700;}
.impact-card .d.bad {background:#FDECEC;color:#B42318;}
.impact-mini {border:1px solid #E3E8EF;border-radius:13px;padding:10px 12px;background:#fff;}
.impact-mini .label {font-size:.76rem;color:#667085;}
.impact-mini .number {font-size:1.18rem;font-weight:800;color:#032F67;}
.impact-note {font-size:.78rem;color:#667085;line-height:1.4;}
.impact-badge {display:inline-block;border-radius:999px;padding:3px 8px;font-size:.72rem;font-weight:700;margin-right:5px;}
.impact-badge.program {background:#EAF7F1;color:#16855B;}
.impact-badge.public {background:#EAF2FF;color:#175CD3;}
.impact-badge.calc {background:#FFF6E8;color:#9A6700;}
.impact-badge.na {background:#F2F4F7;color:#667085;}
@media(max-width:1000px){.impact-grid{grid-template-columns:repeat(2,minmax(0,1fr));}}
@media(max-width:560px){.impact-grid{grid-template-columns:1fr 1fr;gap:8px}.impact-card{padding:10px 11px;min-height:76px}.impact-card .v{font-size:1.2rem}}

.impact-flow {display:grid;grid-template-columns:3fr 1fr 1fr;gap:5px;margin:.45rem 0 .3rem;}
.impact-flow > div {border-radius:10px;padding:8px 10px;font-size:.76rem;font-weight:800;text-align:center;}
.impact-flow .workers {background:#EAF7F1;color:#116A49;}
.impact-flow .business {background:#EEF4FF;color:#175CD3;}
.impact-flow .balance {background:#F3F6F8;color:#344054;}
.impact-strip {border:1px solid #E3E8EF;border-radius:14px;padding:10px 12px;background:#FBFCFD;margin:.3rem 0 .65rem;}
.impact-strip-head {display:flex;justify-content:space-between;gap:10px;align-items:center;margin-bottom:6px;font-size:.78rem;color:#667085;}
.impact-source-row {display:flex;flex-wrap:wrap;gap:6px;margin:.2rem 0 .6rem;}
.impact-source-pill {border:1px solid #E3E8EF;border-radius:999px;padding:4px 8px;font-size:.72rem;color:#475467;background:#fff;}

/* V5.4 — hiérarchie visuelle / avant-après */
.impact-section-title{font-size:.84rem;text-transform:uppercase;letter-spacing:.055em;color:#667085;font-weight:800;margin:.85rem 0 .35rem}
.impact-ba{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px;margin:.4rem 0 .75rem}
.impact-ba-item{background:#FBFCFD;border-top:3px solid #D7DEE8;border-radius:12px;padding:12px 14px;min-width:0}
.impact-ba-item.good{border-top-color:#16855B;background:#F8FCFA}
.impact-ba-item.bad{border-top-color:#B42318;background:#FFF9F9}
.impact-ba-label{font-size:.76rem;color:#667085;margin-bottom:6px}
.impact-ba-values{display:flex;align-items:center;gap:7px;flex-wrap:wrap}
.impact-ba-before{font-size:1rem;color:#667085;font-weight:700}
.impact-ba-arrow{font-size:1.1rem;color:#98A2B3;font-weight:800}
.impact-ba-after{font-size:1.45rem;color:#032F67;font-weight:850;letter-spacing:-.025em}
.impact-ba-item.good .impact-ba-after{color:#16855B}.impact-ba-item.bad .impact-ba-after{color:#B42318}
.impact-ba-delta{margin-top:5px;font-size:.74rem;font-weight:750;color:#667085}
.impact-ba-item.good .impact-ba-delta{color:#16855B}.impact-ba-item.bad .impact-ba-delta{color:#B42318}
.impact-kpi-row{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px;margin:.2rem 0 .75rem}
.impact-kpi{padding:8px 3px 9px;border-bottom:1px solid #E4E7EC;min-width:0}
.impact-kpi .k{font-size:.72rem;color:#667085}.impact-kpi .v{font-size:1.08rem;font-weight:800;color:#032F67;margin-top:2px}.impact-kpi.good .v{color:#16855B}.impact-kpi.bad .v{color:#B42318}.impact-kpi .sub{font-size:.68rem;color:#667085;margin-top:2px}
.impact-flow-shell{background:#FBFCFD;border-radius:14px;padding:13px 14px;margin:.35rem 0 .65rem}
.impact-flow-top{text-align:center;margin-bottom:8px}.impact-flow-top .amount{font-size:1.35rem;font-weight:850;color:#032F67}.impact-flow-top .label{font-size:.73rem;color:#667085}
.impact-flow-arrow{text-align:center;color:#98A2B3;font-size:1.15rem;line-height:1;margin-bottom:5px}
.impact-flow-v54{display:grid;grid-template-columns:3fr 1fr 1fr;gap:7px}
.impact-flow-box{border-radius:11px;padding:10px 8px;text-align:center;min-width:0}.impact-flow-box .pct{font-size:.68rem;font-weight:750}.impact-flow-box .amt{font-size:1rem;font-weight:850;margin:2px 0}.impact-flow-box .lbl{font-size:.68rem}
.impact-flow-box.workers{background:#EAF7F1;color:#116A49}.impact-flow-box.business{background:#EEF4FF;color:#175CD3}.impact-flow-box.balance{background:#F2F4F7;color:#344054}.impact-flow-box.balance.bad{background:#FDECEC;color:#B42318}
.impact-explain{border-left:3px solid #D0D5DD;padding:8px 12px;margin:.5rem 0 .8rem;color:#475467;font-size:.86rem;line-height:1.48}.impact-explain.good{border-left-color:#16855B}.impact-explain.bad{border-left-color:#B42318}
.impact-formula{text-align:center;font-size:.78rem;color:#475467;margin-top:8px;font-weight:700}.impact-equation{display:flex;align-items:stretch;justify-content:center;gap:6px;flex-wrap:wrap}.impact-eq-box{min-width:130px;border-radius:10px;padding:9px 10px;background:#F2F4F7;text-align:center}.impact-eq-box.good{background:#EAF7F1;color:#116A49}.impact-eq-box.bad{background:#FDECEC;color:#B42318}.impact-eq-box .amt{font-size:1rem;font-weight:850}.impact-eq-box .lbl{font-size:.67rem;margin-top:2px}.impact-op{align-self:center;color:#98A2B3;font-weight:850;font-size:1.05rem}
@media(max-width:800px){.impact-ba{grid-template-columns:1fr}.impact-kpi-row{grid-template-columns:repeat(2,minmax(0,1fr))}.impact-flow-v54{grid-template-columns:1fr}.impact-flow-box{display:grid;grid-template-columns:60px 1fr 1fr;align-items:center;text-align:left;gap:5px}}
.impact-compare{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:9px;margin:.4rem 0 .7rem}.impact-compare-card{border:1px solid #E3E8EF;border-radius:14px;padding:11px 12px;background:#fff}.impact-compare-card.selected{border-color:#16855B;background:#F8FCFA}.impact-compare-card .t{font-size:.74rem;color:#667085}.impact-compare-card .n{font-size:1.25rem;font-weight:850;color:#032F67;margin:3px 0}.impact-compare-card .s{font-size:.72rem;color:#667085}.impact-why{border:1px solid #E3E8EF;border-radius:12px;padding:9px 11px;background:#FBFCFD;font-size:.8rem;color:#475467}.impact-share{border:1px dashed #AAB8C8;border-radius:12px;padding:9px 11px;background:#FBFCFD;font-size:.8rem}.impact-share a{font-weight:800;color:#032F67;text-decoration:none}
@media(max-width:650px){.impact-compare{grid-template-columns:1fr}.impact-card .v{font-size:1.1rem}.impact-section-title{margin-top:.7rem}}

</style>
        """,
        unsafe_allow_html=True,
    )


def _card(label: str, value: str, delta: str = "", good: bool = False, bad: bool = False, delta_kind: str = "") -> str:
    state = " bad" if bad else (" good" if good else "")
    cls = f"impact-card{state}"
    d = ""
    if delta:
        dcls = f"d {delta_kind}".strip()
        d = f'<span class="{dcls}">{html.escape(delta)}</span>'
    return (
        f'<div class="{cls}"><div class="k">{html.escape(label)}</div>'
        f'<div class="v">{html.escape(value)}</div>{d}</div>'
    )


def _cards(items: list[dict]):
    cards = "".join(
        _card(
            item["label"],
            item["value"],
            item.get("delta", ""),
            item.get("good", False),
            item.get("bad", False),
            item.get("delta_kind", ""),
        )
        for item in items
    )
    st.markdown(f'<div class="impact-grid">{cards}</div>', unsafe_allow_html=True)


def _badge(level: str) -> str:
    level = (level or "").lower()
    if level == "public_data":
        return '<span class="impact-badge public">Donnée publique</span>'
    if level == "program":
        return '<span class="impact-badge program">Chiffré par le programme</span>'
    if level == "calculation":
        return '<span class="impact-badge calc">Calcul / hypothèse</span>'
    return '<span class="impact-badge na">Non chiffré</span>'


def compute_program_scenario(
    baseline: dict,
    phase: str,
    use_spending: bool = True,
    use_workers: bool = True,
    use_production: bool = True,
    realization_pct: float = 100.0,
) -> dict:
    """Calcul mécanique du scénario agrégé. Aucun effet de croissance n'est appliqué.

    ``realization_pct`` est un stress-test : il modifie uniquement le montant
    d'économies effectivement réalisé. Les baisses de prélèvements restent au
    niveau prévu pour l'horizon choisi afin de rendre visible un éventuel écart
    de financement. 100 % reproduit exactement le scénario de référence.
    """
    phase_ratio = _phase_ratio(phase)
    target_savings = 200.0 * phase_ratio
    realization_pct = max(0.0, min(100.0, float(realization_pct)))
    spending_savings = target_savings * realization_pct / 100.0 if use_spending else 0.0
    worker_relief = target_savings * 0.60 if use_workers else 0.0
    production_relief = target_savings * 0.20 if use_production else 0.0

    deficit_before = float(baseline["deficit_billion"])
    spending_before = float(baseline["spending_billion"])
    revenue_before = float(baseline["revenue_billion"])
    debt_before = float(baseline["debt_billion"])
    gdp = float(baseline["gdp_billion"])
    po_before = float(baseline["mandatory_levies_pct_gdp"])

    spending_after = spending_before - spending_savings
    revenue_after = revenue_before - worker_relief - production_relief
    deficit_after = spending_after - revenue_after
    deficit_improvement = deficit_before - deficit_after

    po_amount_before = po_before / 100.0 * gdp
    po_amount_after = po_amount_before - worker_relief - production_relief
    po_after = max(0.0, po_amount_after / gdp * 100.0)
    spending_pct_after = spending_after / gdp * 100.0
    deficit_pct_after = deficit_after / gdp * 100.0

    debt_next = debt_before + max(deficit_after, 0.0)
    debt_next_pct = debt_next / gdp * 100.0
    three_pct_deficit = gdp * 0.03
    gap_to_three_pct = max(0.0, deficit_after - three_pct_deficit)
    relief_total = worker_relief + production_relief
    funding_gap = spending_savings - relief_total
    funding_coverage_pct = 100.0 if relief_total <= 0 else spending_savings / relief_total * 100.0

    return {
        "phase_ratio": phase_ratio,
        "target_savings": target_savings,
        "realization_pct": realization_pct,
        "spending_savings": spending_savings,
        "worker_relief": worker_relief,
        "production_relief": production_relief,
        "deficit_before": deficit_before,
        "deficit_after": deficit_after,
        "deficit_improvement": deficit_improvement,
        "spending_before": spending_before,
        "spending_after": spending_after,
        "spending_pct_after": spending_pct_after,
        "revenue_before": revenue_before,
        "revenue_after": revenue_after,
        "po_before": po_before,
        "po_after": po_after,
        "deficit_pct_after": deficit_pct_after,
        "debt_before": debt_before,
        "debt_next": debt_next,
        "debt_next_pct": debt_next_pct,
        "gdp": gdp,
        "gap_to_three_pct": gap_to_three_pct,
        "three_pct_deficit": three_pct_deficit,
        "relief_total": relief_total,
        "funding_gap": funding_gap,
        "funding_coverage_pct": funding_coverage_pct,
    }


def compute_household_impact(
    monthly_income: float,
    salaried_workers: int,
    adults: int,
    children_u14: int,
    children_14p: int,
    phase: str,
    include_salary_relief: bool,
    retirement_floor: float = 0.0,
    teacher_raise_pct: float = 0.0,
) -> dict:
    ratio = _phase_ratio(phase)
    salary_gain = 400.0 * ratio * max(0, salaried_workers) if include_salary_relief else 0.0
    retirement_gain = max(0.0, retirement_floor - monthly_income) if retirement_floor else 0.0
    teacher_gain = monthly_income * teacher_raise_pct / 100.0 if teacher_raise_pct else 0.0
    change = salary_gain + retirement_gain + teacher_gain
    after = monthly_income + change
    uc = 1.0 + max(0, adults - 1) * 0.5 + max(0, children_14p) * 0.5 + max(0, children_u14) * 0.3
    living_before = monthly_income / uc if uc else monthly_income
    living_after = after / uc if uc else after
    return {
        "salary_gain": salary_gain,
        "retirement_gain": retirement_gain,
        "teacher_gain": teacher_gain,
        "change": change,
        "after": after,
        "uc": uc,
        "living_before": living_before,
        "living_after": living_after,
    }


def compute_five_year_trajectory(
    baseline: dict,
    use_spending: bool = True,
    use_workers: bool = True,
    use_production: bool = True,
    realization_pct: float = 100.0,
) -> pd.DataFrame:
    """Trajectoire mécanique sur cinq ans, à PIB constant.

    Années 2-4 : interpolation linéaire entre 80 Md€ en année 1 et 200 Md€ en année 5.
    Aucune croissance, inflation ou réaction comportementale n'est ajoutée.
    """
    rows = []
    debt = float(baseline["debt_billion"])
    debt_without = float(baseline["debt_billion"])
    baseline_deficit = float(baseline["deficit_billion"])
    for phase in PHASE_LABELS:
        sc = compute_program_scenario(baseline, phase, use_spending, use_workers, use_production, realization_pct=realization_pct)
        debt += max(sc["deficit_after"], 0.0)
        debt_without += max(baseline_deficit, 0.0)
        rows.append({
            "Année": phase,
            "Économies (Md€)": sc["spending_savings"],
            "Baisse prélèvements actifs (Md€)": sc["worker_relief"],
            "Baisse impôts production (Md€)": sc["production_relief"],
            "Déficit (Md€)": sc["deficit_after"],
            "Déficit / PIB (%)": sc["deficit_pct_after"],
            "Dette mécanique (Md€)": debt,
            "Dette sans mesures (Md€)": debt_without,
            "Écart de dette vs référence (Md€)": debt_without - debt,
            "Statut": "Hypothèse linéaire" if _phase_is_estimated(phase) else "Repère du programme",
        })
    return pd.DataFrame(rows)


def _quantified_measure(m: dict) -> bool:
    return str(m.get("confidence", "")).lower() != "non_quantified" and bool(m.get("headline"))


def _measure_summary(measures: list[dict]) -> dict:
    total = len(measures)
    quantified = sum(1 for m in measures if _quantified_measure(m))
    sourced = sum(1 for m in measures if m.get("source_url"))
    directly_modeled = sum(
        1 for m in measures
        if any(k in str(m.get("budget_treatment", "")).lower() for k in ("scénario", "impact ménage", "impact enseignant"))
    )
    return {"total": total, "quantified": quantified, "sourced": sourced, "modeled": directly_modeled}


def _trend_state(before: float, after: float, lower_is_better: bool = True, tolerance: float = 1e-9) -> str:
    diff = after - before
    if abs(diff) <= tolerance:
        return "neutral"
    favorable = diff < 0 if lower_is_better else diff > 0
    return "good" if favorable else "bad"


def _delta_text(before: float, after: float, unit: str = "Md€", lower_is_better: bool = True) -> str:
    diff = after - before
    if abs(diff) < 1e-9:
        return f"= 0 {unit}" if unit else "inchangé"
    arrow = "↓" if diff < 0 else "↑"
    val = abs(diff)
    num = f"{val:.1f}".replace(".0", "").replace(".", ",")
    return f"{arrow} {num} {unit}".strip()


def _render_before_after(baseline: dict, scenario: dict):
    items = [
        ("Déficit public", float(scenario["deficit_before"]), float(scenario["deficit_after"]), "Md€", True, fmt_bn),
        ("Dépenses publiques / PIB", float(baseline["spending_pct_gdp"]), float(scenario["spending_pct_after"]), "pt", True, fmt_pct),
        ("Prélèvements / PIB*", float(baseline["mandatory_levies_pct_gdp"]), float(scenario["po_after"]), "pt", True, fmt_pct),
    ]
    blocks=[]
    for label,before,after,unit,lower_better,formatter in items:
        state=_trend_state(before,after,lower_better)
        delta=_delta_text(before,after,unit,lower_better)
        blocks.append(
            f'<div class="impact-ba-item {state}"><div class="impact-ba-label">{html.escape(label)}</div>'
            f'<div class="impact-ba-values"><span class="impact-ba-before">{formatter(before)}</span>'
            f'<span class="impact-ba-arrow">→</span><span class="impact-ba-after">{formatter(after)}</span></div>'
            f'<div class="impact-ba-delta">{html.escape(delta)}</div></div>'
        )
    st.markdown('<div class="impact-section-title">Avant → après</div><div class="impact-ba">'+''.join(blocks)+'</div>',unsafe_allow_html=True)


def _render_compact_kpis(scenario: dict):
    improvement=float(scenario["deficit_improvement"])
    state="good" if improvement>1e-9 else ("bad" if improvement<-1e-9 else "")
    balance_label="Solde public amélioré" if improvement>1e-9 else ("Solde public dégradé" if improvement<-1e-9 else "Solde public")
    balance_sub="déficit ↓" if improvement>1e-9 else ("déficit ↑" if improvement<-1e-9 else "inchangé")
    kpis=[
        ("Économies de dépenses", fmt_bn(scenario["spending_savings"]), "dépenses ↓" if scenario["spending_savings"] else "non activées", "good" if scenario["spending_savings"] else ""),
        ("Prélèvements actifs", fmt_bn(scenario["worker_relief"]), "prélèvements ↓" if scenario["worker_relief"] else "non activés", "good" if scenario["worker_relief"] else ""),
        ("Impôts de production", fmt_bn(scenario["production_relief"]), "impôts ↓" if scenario["production_relief"] else "non activés", "good" if scenario["production_relief"] else ""),
        (balance_label, fmt_bn(abs(improvement)), balance_sub, state),
    ]
    out=[]
    for label,value,sub,stt in kpis:
        out.append(f'<div class="impact-kpi {stt}"><div class="k">{html.escape(label)}</div><div class="v">{html.escape(value)}</div><div class="sub">{html.escape(sub)}</div></div>')
    st.markdown('<div class="impact-kpi-row">'+''.join(out)+'</div>',unsafe_allow_html=True)


def _render_allocation_flow(scenario: dict, program_mode: bool):
    total=float(scenario.get("target_savings",0.0) or 0.0)
    improvement=float(scenario.get("deficit_improvement",0.0) or 0.0)
    if program_mode:
        block=(
            '<div class="impact-section-title">Où vont les économies ?</div>'
            '<div class="impact-flow-shell">'
            f'<div class="impact-flow-top"><div class="amount">{fmt_bn(total)}</div><div class="label">Économies de dépenses prévues à cet horizon</div></div>'
            '<div class="impact-flow-arrow">↓</div><div class="impact-flow-v54">'
            f'<div class="impact-flow-box workers"><div class="pct">60 %</div><div class="amt">{fmt_bn(scenario["worker_relief"])}</div><div class="lbl">Baisse prélèvements actifs</div></div>'
            f'<div class="impact-flow-box business"><div class="pct">20 %</div><div class="amt">{fmt_bn(scenario["production_relief"])}</div><div class="lbl">Baisse impôts production</div></div>'
            f'<div class="impact-flow-box balance"><div class="pct">20 %</div><div class="amt">{fmt_bn(max(0.0, improvement))}</div><div class="lbl">Amélioration du solde</div></div>'
            '</div>'
            f'<div class="impact-formula">{fmt_bn(scenario["spending_savings"])} d’économies − {fmt_bn(scenario["worker_relief"])} de prélèvements − {fmt_bn(scenario["production_relief"])} d’impôts = {fmt_bn(improvement, signed=True)} sur le solde</div>'
            '</div>'
        )
    else:
        net_state='good' if improvement>1e-9 else ('bad' if improvement<-1e-9 else '')
        net_label='déficit réduit' if improvement>1e-9 else ('déficit augmenté' if improvement<-1e-9 else 'solde inchangé')
        block=(
            '<div class="impact-section-title">Bilan mécanique du scénario</div>'
            '<div class="impact-flow-shell"><div class="impact-equation">'
            f'<div class="impact-eq-box good"><div class="amt">+ {fmt_bn(scenario["spending_savings"])}</div><div class="lbl">économies de dépenses</div></div>'
            '<div class="impact-op">−</div>'
            f'<div class="impact-eq-box"><div class="amt">{fmt_bn(scenario["worker_relief"])}</div><div class="lbl">baisse prélèvements actifs</div></div>'
            '<div class="impact-op">−</div>'
            f'<div class="impact-eq-box"><div class="amt">{fmt_bn(scenario["production_relief"])}</div><div class="lbl">baisse impôts production</div></div>'
            '<div class="impact-op">=</div>'
            f'<div class="impact-eq-box {net_state}"><div class="amt">{fmt_bn(abs(improvement))}</div><div class="lbl">{html.escape(net_label)}</div></div>'
            '</div></div>'
        )
    st.markdown(block,unsafe_allow_html=True)


def _render_progress_to_targets(baseline: dict, scenario: dict):
    base_def = float(baseline["deficit_billion"])
    current = float(scenario["deficit_after"])
    improvement = max(0.0, base_def - current)
    pct_balance = min(100.0, improvement / max(base_def, 0.001) * 100.0)
    three_target = float(scenario["three_pct_deficit"])
    need_three = max(0.001, base_def - three_target)
    pct_three = 100.0 if current <= three_target else min(100.0, improvement / need_three * 100.0)
    c1, c2 = st.columns(2)
    with c1:
        st.caption(f"Vers 3 % du PIB · {pct_three:.0f} % du chemin mécanique")
        st.progress(int(round(pct_three)))
    with c2:
        st.caption(f"Vers l'équilibre · {pct_balance:.0f} % du déficit initial résorbé")
        st.progress(int(round(pct_balance)))


def _render_sources(measures: list[dict], only_quantified: bool):
    shown = [m for m in measures if (not only_quantified or _quantified_measure(m))]
    stats = _measure_summary(measures)
    st.markdown("### Sources et niveau de précision")
    st.markdown(
        f'<div class="impact-source-row"><span class="impact-source-pill">{stats["total"]} mesures / objectifs</span>'
        f'<span class="impact-source-pill">{stats["quantified"]} avec repère chiffré</span>'
        f'<span class="impact-source-pill">{stats["sourced"]} avec lien source</span>'
        f'<span class="impact-source-pill">{stats["modeled"]} à effet direct modélisé</span></div>',
        unsafe_allow_html=True,
    )
    rows=[]
    for m in shown:
        rows.append({
            "Thème": m.get("category", ""),
            "Mesure": m.get("title", ""),
            "Repère": m.get("headline", "—"),
            "Statut": {"program":"Programme", "public_data":"Donnée publique", "calculation":"Calcul / hypothèse", "non_quantified":"Non chiffré"}.get(m.get("confidence"), "À préciser"),
            "Traitement": m.get("budget_treatment", "—"),
            "Source": m.get("source_url", ""),
        })
    df=pd.DataFrame(rows)
    if df.empty:
        st.info("Aucune mesure ne correspond au filtre.")
        return
    cfg={}
    if hasattr(st.column_config, "LinkColumn"):
        cfg["Source"] = st.column_config.LinkColumn("Source", display_text="Ouvrir")
    st.dataframe(df, hide_index=True, width="stretch", height=min(520, 36*(len(df)+1)), column_config=cfg)
    st.caption("Un repère chiffré n'est pas automatiquement un impact budgétaire calculable. Les sous-mesures susceptibles d'être comprises dans les 200 Md€ ne sont pas additionnées une seconde fois.")


def _render_program_numbers(measures: list[dict]):
    rows = []
    for m in measures:
        if m.get("headline"):
            rows.append(
                {
                    "Thème": m.get("category", "Autre"),
                    "Mesure / objectif": m.get("title", ""),
                    "Repère": m.get("headline", ""),
                    "Nature": {
                        "program": "Programme chiffré",
                        "public_data": "Donnée publique",
                        "calculation": "Calculable / hypothèse",
                    }.get(m.get("confidence"), "Non chiffré"),
                    "Effet budget agrégé": m.get("budget_treatment", "Non intégré"),
                }
            )
    df = pd.DataFrame(rows)
    st.dataframe(df, width="stretch", hide_index=True, height=min(430, 38 * (len(df) + 1)))


def _render_measure_detail(measures: list[dict]):
    options = {f"{m.get('icon','•')} {m.get('title','Mesure')}": m for m in measures}
    choice = st.selectbox("Voir le détail d’une mesure", list(options), key="impact_measure_detail")
    m = options[choice]
    with st.container(border=True):
        st.markdown(_badge(m.get("confidence", "")), unsafe_allow_html=True)
        st.markdown(f"**{m.get('headline','')}** — {m.get('summary','')}")
        if m.get("impact_note"):
            st.caption(m["impact_note"])
        st.markdown(f"**Source :** [{m.get('source_label','Source')}]({m.get('source_url','#')})")
        st.markdown(f"**Méthode :** {m.get('methodology','Aucune méthode définie.')}")
        if m.get("limits"):
            st.warning(m["limits"])


def _render_budget_waterfall(scenario: dict):
    """Décompose le passage du déficit initial au déficit simulé."""
    before = float(scenario["deficit_before"])
    savings = float(scenario["spending_savings"])
    workers = float(scenario["worker_relief"])
    production = float(scenario["production_relief"])
    after = float(scenario["deficit_after"])

    fig = go.Figure(
        go.Waterfall(
            name="",
            orientation="v",
            measure=["absolute", "relative", "relative", "relative", "total"],
            x=["Déficit initial", "Économies", "Prélèvements actifs", "Impôts production", "Déficit final"],
            y=[before, -savings, workers, production, 0],
            text=[fmt_bn(before), f"−{fmt_bn(savings)}", f"+{fmt_bn(workers)}", f"+{fmt_bn(production)}", fmt_bn(after)],
            textposition="outside",
            connector={"line": {"color": "#D0D5DD", "width": 1}},
            decreasing={"marker": {"color": GREEN}},
            increasing={"marker": {"color": RED}},
            totals={"marker": {"color": NAVY}},
            hovertemplate="%{x}<br>%{text}<extra></extra>",
        )
    )
    fig.update_layout(
        height=360,
        margin=dict(l=10, r=10, t=20, b=10),
        showlegend=False,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        yaxis_title="Déficit (Md€)",
    )
    st.markdown('<div class="impact-section-title">Comment le déficit évolue</div>', unsafe_allow_html=True)
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
    st.caption("Lecture : les économies réduisent le déficit ; les baisses de prélèvements réduisent les recettes et l'augmentent mécaniquement. Aucun effet macroéconomique indirect n'est ajouté.")


def _render_scenario_comparison(baseline: dict, phase: str, selected_pct: float):
    values = []
    for label, pct in [("Programme · 100 %", 100.0), (f"Votre test · {selected_pct:.0f} %", float(selected_pct)), ("Stress-test · 75 %", 75.0)]:
        sc = compute_program_scenario(baseline, phase, True, True, True, realization_pct=pct)
        values.append((label, pct, sc))
    cards = []
    for label, pct, sc in values:
        state = " selected" if abs(pct-selected_pct) < 1e-9 else ""
        delta = sc["deficit_after"] - sc["deficit_before"]
        direction = f"↓ {fmt_bn(abs(delta))}" if delta < 0 else (f"↑ {fmt_bn(abs(delta))}" if delta > 0 else "inchangé")
        cards.append(f'<div class="impact-compare-card{state}"><div class="t">{html.escape(label)}</div><div class="n">{fmt_bn(sc["deficit_after"])}</div><div class="s">Déficit · {html.escape(direction)} · économies {fmt_bn(sc["spending_savings"])}</div></div>')
    st.markdown('<div class="impact-section-title">Comparer les scénarios</div><div class="impact-compare">'+''.join(cards)+'</div>', unsafe_allow_html=True)
    df = pd.DataFrame([{
        "Scénario": label,
        "Économies réalisées (Md€)": sc["spending_savings"],
        "Déficit (Md€)": sc["deficit_after"],
        "Déficit / PIB (%)": sc["deficit_pct_after"],
        "Couverture des baisses de prélèvements (%)": sc["funding_coverage_pct"],
    } for label, _, sc in values])
    fig = px.bar(df, x="Scénario", y="Déficit (Md€)", text_auto=".1f", title="Déficit selon le niveau de réalisation des économies")
    fig.update_layout(height=285, margin=dict(l=5,r=5,t=42,b=5), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", showlegend=False)
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})


def _render_why_this_number(scenario: dict):
    with st.expander("❓ Pourquoi ce chiffre ?", expanded=False):
        st.markdown(
            f'<div class="impact-why"><b>Déficit simulé = déficit initial − économies réalisées + baisses de recettes.</b><br><br>'
            f'{fmt_bn(scenario["deficit_before"])} − {fmt_bn(scenario["spending_savings"])} + {fmt_bn(scenario["worker_relief"])} + {fmt_bn(scenario["production_relief"])} = <b>{fmt_bn(scenario["deficit_after"])}</b>.<br><br>'
            f'Le chiffre est un calcul mécanique à PIB constant. Aucun effet de croissance, d’inflation, d’emploi ou de comportement n’est ajouté.</div>',
            unsafe_allow_html=True,
        )


def _render_share_link(phase: str, realization_pct: float, scenario_mode: str, use_spending: bool, use_workers: bool, use_production: bool):
    mode = "programme" if scenario_mode == "Programme publié" else "personnalise"
    year = _phase_number(phase)
    href = (f'?page=simulateur&year={year}&realisation={int(round(realization_pct))}&mode={mode}'
            f'&spend={1 if use_spending else 0}&workers={1 if use_workers else 0}&prod={1 if use_production else 0}')
    st.markdown(f'<div class="impact-share">🔗 <a href="{href}" target="_self">Lien partageable vers ce scénario</a><br><span style="color:#667085">Le lien mémorise l’année, le taux de réalisation, le mode et les leviers activés.</span></div>', unsafe_allow_html=True)


def _render_france(baseline: dict, measures: list[dict], phase: str):
    """Vue France simplifiée : le scénario publié est montré d'abord,
    les stress-tests et détails restent disponibles mais repliés.
    """
    scenario_mode = "Programme publié"
    use_spending = use_workers = use_production = True
    realization_pct = 100

    st.markdown("### Le scénario en une lecture")
    st.caption("Par défaut, vous voyez le scénario publié. Les réglages avancés sont facultatifs.")

    with st.expander("⚙️ Tester un scénario différent", expanded=False):
        activate_test = st.toggle(
            "Activer le mode test",
            value=False,
            key=f"impact_activate_test_{phase}",
            help="Permet de tester une réalisation partielle des économies ou de désactiver certains leviers. Ce n'est plus nécessairement le programme publié.",
        )
        if activate_test:
            if hasattr(st, "segmented_control"):
                scenario_mode = st.segmented_control(
                    "Type de test",
                    ["Programme publié", "Personnaliser"],
                    default="Programme publié",
                    key="impact_scenario_mode",
                ) or "Programme publié"
            else:
                scenario_mode = st.radio(
                    "Type de test",
                    ["Programme publié", "Personnaliser"],
                    horizontal=True,
                    key="impact_scenario_mode",
                )

            if scenario_mode == "Personnaliser":
                c1, c2, c3 = st.columns(3)
                use_spending = c1.toggle("Économies de dépenses", value=True, key=f"impact_spend_{phase}")
                use_workers = c2.toggle("Baisse prélèvements actifs", value=True, key=f"impact_workers_{phase}")
                use_production = c3.toggle("Baisse impôts production", value=True, key=f"impact_prod_{phase}")

            realization_pct = st.slider(
                "Part des économies effectivement réalisées",
                min_value=50,
                max_value=100,
                value=100,
                step=5,
                key=f"impact_realization_{phase}_{scenario_mode}",
                help="Stress-test : les baisses de prélèvements restent au niveau prévu afin de rendre visible un éventuel manque de financement.",
            )
            st.caption("Ce réglage sert à comprendre la mécanique budgétaire ; il ne constitue pas une prévision.")

    program_mode = scenario_mode == "Programme publié"
    scenario = compute_program_scenario(
        baseline,
        phase,
        use_spending,
        use_workers,
        use_production,
        realization_pct=realization_pct,
    )

    improvement = float(scenario["deficit_improvement"])
    if improvement > 1e-9:
        summary = (
            f"À {phase.lower()}, le déficit passe mécaniquement de {fmt_bn(scenario['deficit_before'])} "
            f"à {fmt_bn(scenario['deficit_after'])}, soit {fmt_bn(improvement)} de déficit en moins."
        )
        st.success(summary)
    elif improvement < -1e-9:
        st.error(
            f"Dans ce test, le déficit augmente mécaniquement de {fmt_bn(abs(improvement))} : "
            f"{fmt_bn(scenario['deficit_before'])} → {fmt_bn(scenario['deficit_after'])}."
        )
    else:
        st.info(f"Dans ce scénario, le déficit reste mécaniquement à {fmt_bn(scenario['deficit_after'])}.")

    _render_before_after(baseline, scenario)
    _render_allocation_flow(scenario, program_mode and realization_pct == 100)

    st.caption("Lecture mécanique à PIB constant : aucune croissance, réaction comportementale ou effet d'emploi n'est ajouté.")

    with st.expander("❓ Comprendre le calcul", expanded=False):
        _render_compact_kpis(scenario)
        _render_why_this_number(scenario)
        _render_budget_waterfall(scenario)
        _render_progress_to_targets(baseline, scenario)
        if program_mode:
            _render_scenario_comparison(baseline, phase, realization_pct)

    with st.expander("📈 Voir la trajectoire sur 5 ans", expanded=False):
        trajectory = compute_five_year_trajectory(
            baseline,
            use_spending,
            use_workers,
            use_production,
            realization_pct=realization_pct,
        )
        traj_plot = trajectory[["Année", "Déficit (Md€)"]].rename(columns={"Déficit (Md€)": "Avec les mesures"})
        traj_plot["Sans mesures"] = float(baseline["deficit_billion"])
        melted = traj_plot.melt(id_vars="Année", var_name="Scénario", value_name="Déficit (Md€)")
        fig_traj = px.line(melted, x="Année", y="Déficit (Md€)", color="Scénario", markers=True)
        fig_traj.add_hline(
            y=float(baseline["gdp_billion"]) * 0.03,
            line_dash="dot",
            annotation_text="Repère 3 % du PIB",
            annotation_position="bottom right",
        )
        fig_traj.update_layout(
            height=330,
            margin=dict(l=5, r=5, t=20, b=5),
            legend_title_text="",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            hovermode="x unified",
        )
        st.plotly_chart(fig_traj, width="stretch", config={"displayModeBar": False})
        st.caption("Années 2 à 4 : interpolation linéaire de visualisation entre les repères Année 1 et Année 5.")

        with st.expander("Voir le détail annuel", expanded=False):
            st.dataframe(
                trajectory[["Année", "Économies (Md€)", "Déficit (Md€)", "Déficit / PIB (%)", "Écart de dette vs référence (Md€)", "Statut"]],
                hide_index=True,
                width="stretch",
                height=245,
                column_config={
                    "Économies (Md€)": st.column_config.NumberColumn(format="%.0f"),
                    "Déficit (Md€)": st.column_config.NumberColumn(format="%.1f"),
                    "Déficit / PIB (%)": st.column_config.NumberColumn(format="%.1f %%"),
                    "Écart de dette vs référence (Md€)": st.column_config.NumberColumn(format="%.1f"),
                },
            )

    with st.expander("📚 Programme en chiffres et détails", expanded=False):
        st.caption("Les sous-mesures susceptibles d'être comprises dans l'enveloppe de 200 Md€ ne sont pas additionnées une seconde fois.")
        _render_program_numbers(measures)
        _render_measure_detail(measures)

    if _phase_is_estimated(phase):
        st.caption(
            f"{phase} : {scenario['target_savings']:.0f} Md€ est une interpolation de visualisation entre 80 Md€ en Année 1 et 200 Md€ en Année 5."
        )

def _person_direct_impact(monthly_income: float, status: str, phase: str) -> dict:
    """Effets directs individuels uniquement, sans comportement ni fiscalité complète."""
    ratio = _phase_ratio(phase)
    salary_gain = 400.0 * ratio if status in ("Salarié", "Enseignant") else 0.0
    teacher_gain = monthly_income * 0.20 if status == "Enseignant" and _phase_number(phase) >= 5 else 0.0
    retirement_gain = max(0.0, 1200.0 - monthly_income) if status == "Retraité" and _phase_number(phase) >= 5 else 0.0
    total_gain = salary_gain + teacher_gain + retirement_gain
    return {
        "status": status,
        "income": monthly_income,
        "salary_gain": salary_gain,
        "teacher_gain": teacher_gain,
        "retirement_gain": retirement_gain,
        "total_gain": total_gain,
        "after": monthly_income + total_gain,
    }


def _render_household_before_after(before: float, after: float, uc: float):
    annual_before = before * 12.0
    annual_after = after * 12.0
    living_before = annual_before / uc if uc else annual_before
    living_after = annual_after / uc if uc else annual_after
    gain_monthly = after - before
    gain_annual = annual_after - annual_before
    living_delta_pct = ((living_after / living_before) - 1.0) * 100.0 if living_before else None

    items = [
        ("Revenu du ménage / mois", fmt_eur(before), fmt_eur(after), fmt_eur(gain_monthly, signed=True) + "/mois"),
        ("Revenu du ménage / an", fmt_eur(annual_before), fmt_eur(annual_after), fmt_eur(gain_annual, signed=True) + "/an"),
        ("Niveau de vie annuel / UC", fmt_eur(living_before), fmt_eur(living_after), fmt_pct(living_delta_pct, signed=True) if living_delta_pct is not None else "—"),
    ]
    blocks=[]
    for label,bef,aft,delta in items:
        state="good" if aft != bef and after > before else ("bad" if aft != bef and after < before else "")
        blocks.append(
            f'<div class="impact-ba-item {state}"><div class="impact-ba-label">{html.escape(label)}</div>'
            f'<div class="impact-ba-values"><span class="impact-ba-before">{html.escape(bef)}</span>'
            f'<span class="impact-ba-arrow">→</span><span class="impact-ba-after">{html.escape(aft)}</span></div>'
            f'<div class="impact-ba-delta">{html.escape(delta)}</div></div>'
        )
    st.markdown('<div class="impact-section-title">Votre avant → après</div><div class="impact-ba">'+''.join(blocks)+'</div>', unsafe_allow_html=True)
    return {
        "annual_before": annual_before,
        "annual_after": annual_after,
        "living_before": living_before,
        "living_after": living_after,
        "gain_monthly": gain_monthly,
        "gain_annual": gain_annual,
        "living_delta_pct": living_delta_pct,
    }


def _render_you(phase: str):
    st.markdown("### Votre ménage")
    st.caption("Simulation anonyme : aucune donnée personnelle n'est enregistrée. Les montants affichés sont des effets directs simplifiés à partir des seules mesures actuellement modélisables.")

    situation = st.segmented_control("Situation", ["Seul", "Couple"], default="Seul", key="impact_household_situation") if hasattr(st, "segmented_control") else st.radio("Situation", ["Seul", "Couple"], horizontal=True, key="impact_household_situation")
    if not situation:
        situation = "Seul"

    p1, p2 = st.columns(2)
    with p1:
        status1 = st.selectbox("Votre statut", ["Salarié", "Enseignant", "Retraité", "Indépendant", "Sans activité"], key="impact_status_1")
        income1 = st.number_input("Votre revenu net / disponible mensuel (€)", min_value=0.0, max_value=100000.0, value=2200.0, step=50.0, key="impact_income_1")
    partner = None
    if situation == "Couple":
        with p2:
            status2 = st.selectbox("Statut du conjoint", ["Salarié", "Enseignant", "Retraité", "Indépendant", "Sans activité"], key="impact_status_2")
            income2 = st.number_input("Revenu net / disponible du conjoint (€)", min_value=0.0, max_value=100000.0, value=1800.0, step=50.0, key="impact_income_2")
            partner = _person_direct_impact(income2, status2, phase)
    else:
        with p2:
            st.info("Passez en mode Couple pour ajouter le conjoint au calcul du revenu et du niveau de vie.")

    c1, c2 = st.columns(2)
    children_u14 = c1.number_input("Enfants de moins de 14 ans", 0, 10, 0, key="impact_kids_u14_v55")
    children_14p = c2.number_input("Enfants de 14 ans ou plus", 0, 10, 0, key="impact_kids_14p_v55")

    person = _person_direct_impact(income1, status1, phase)
    adults = 2 if situation == "Couple" else 1
    before = person["income"] + (partner["income"] if partner else 0.0)
    after = person["after"] + (partner["after"] if partner else 0.0)
    uc = 1.0 + max(0, adults - 1) * 0.5 + int(children_14p) * 0.5 + int(children_u14) * 0.3

    summary = _render_household_before_after(before, after, uc)
    st.caption(f"Unités de consommation utilisées : {uc:.1f} UC (1 pour le premier adulte, 0,5 pour le second et les personnes ≥14 ans, 0,3 pour les enfants <14 ans). Le niveau de vie est présenté sur une base annuelle par UC.")

    rows=[]
    for label, r in [("Vous", person), ("Conjoint", partner)]:
        if not r:
            continue
        rows.append({
            "Personne": label,
            "Statut": r["status"],
            "Revenu avant": r["income"],
            "Cotisations / travail": r["salary_gain"],
            "Enseignant": r["teacher_gain"],
            "Retraite": r["retirement_gain"],
            "Gain direct": r["total_gain"],
            "Revenu après": r["after"],
        })
    rdf=pd.DataFrame(rows)
    st.markdown("#### D'où vient la variation ?")
    st.dataframe(
        rdf,
        hide_index=True,
        width="stretch",
        column_config={
            "Revenu avant": st.column_config.NumberColumn(format="%.0f €"),
            "Cotisations / travail": st.column_config.NumberColumn(format="%+.0f €"),
            "Enseignant": st.column_config.NumberColumn(format="%+.0f €"),
            "Retraite": st.column_config.NumberColumn(format="%+.0f €"),
            "Gain direct": st.column_config.NumberColumn(format="%+.0f €"),
            "Revenu après": st.column_config.NumberColumn(format="%.0f €"),
        },
    )

    with st.expander("❓ Pourquoi ce chiffre pour mon ménage ?", expanded=False):
        parts = []
        for label, r in [("Vous", person), ("Conjoint", partner)]:
            if not r:
                continue
            detail = []
            if r["salary_gain"]:
                detail.append(f"{fmt_eur(r['salary_gain'], signed=True)} cotisations / travail")
            if r["teacher_gain"]:
                detail.append(f"{fmt_eur(r['teacher_gain'], signed=True)} revalorisation enseignant")
            if r["retirement_gain"]:
                detail.append(f"{fmt_eur(r['retirement_gain'], signed=True)} retraite")
            parts.append(f"**{label}** : " + (" + ".join(detail) if detail else "aucun effet monétaire direct modélisé"))
        st.markdown("  \n".join(parts))
        st.caption(f"Total ménage : {fmt_eur(summary['gain_monthly'], signed=True)}/mois, soit {fmt_eur(summary['gain_annual'], signed=True)}/an. Niveau de vie : {fmt_pct(summary['living_delta_pct'], signed=True) if summary['living_delta_pct'] is not None else '—'}.")

    if status1 in ("Salarié", "Enseignant") or (partner and partner["status"] in ("Salarié", "Enseignant")):
        gain_per_worker = 400.0 * _phase_ratio(phase)
        if _phase_is_estimated(phase):
            txt=f"{gain_per_worker:.0f} € par actif salarié est une interpolation de visualisation pour {phase}."
        elif _phase_number(phase) == 1:
            txt="160 € par actif salarié en Année 1 est une hypothèse proportionnelle 80/200."
        else:
            txt="Presque 400 € nets par salarié à la cible est l'ordre de grandeur publié utilisé par le simulateur."
        st.caption(txt + " Ce n'est pas un barème individuel de paie.")

    if (status1 == "Enseignant" or (partner and partner["status"] == "Enseignant")) and _phase_number(phase) < 5:
        st.warning("La revalorisation enseignant de +20 % est annoncée en cinq ans, mais le calendrier annuel n'est pas documenté dans la source utilisée. Elle n'est donc appliquée qu'en Année 5.")
    if status1 == "Retraité" or (partner and partner["status"] == "Retraité"):
        st.caption("Pour la cible retraite, le module utilise un socle autour de 1 200 € lorsqu'il est applicable. Cette hypothèse est explicitement signalée dans les sources du simulateur.")

    st.markdown("#### Lecture rapide")
    if summary["gain_annual"] > 0:
        st.success(f"Dans ce scénario, le revenu disponible direct du ménage augmente de {fmt_eur(summary['gain_annual'])} par an, soit {fmt_eur(summary['gain_monthly'])} par mois. Le niveau de vie annuel par UC augmente de {fmt_pct(summary['living_delta_pct'])}.")
    elif summary["gain_annual"] < 0:
        st.error(f"Dans ce scénario, le revenu disponible direct du ménage diminue de {fmt_eur(abs(summary['gain_annual']))} par an.")
    else:
        st.info("Aucun effet monétaire direct actuellement documenté n'est appliqué à ce ménage pour cet horizon.")

def _render_profiles(phase: str):
    st.markdown("### Comparer des profils")
    st.caption("Ordres de grandeur : ils illustrent les effets directement modélisés, pas l’ensemble des conséquences économiques du programme.")
    ratio = _phase_ratio(phase)
    salary_gain = 400.0 * ratio
    rows = [
        {"Profil": "SMIC 2026", "Avant": 1477.93, "Après": 1477.93 + salary_gain, "Variation": salary_gain, "Hypothèse": "1 actif salarié"},
        {"Profil": "Salaire médian privé", "Avant": 2190.0, "Après": 2190.0 + salary_gain, "Variation": salary_gain, "Hypothèse": "1 actif salarié"},
        {"Profil": "Cadre moyen privé", "Avant": 4629.0, "Après": 4629.0 + salary_gain, "Variation": salary_gain, "Hypothèse": "1 actif salarié"},
        {"Profil": "Famille · 2 salaires médians", "Avant": 4380.0, "Après": 4380.0 + salary_gain * 2, "Variation": salary_gain * 2, "Hypothèse": "2 actifs salariés"},
        {"Profil": "Retraité à 1 000 €", "Avant": 1000.0, "Après": 1200.0 if _phase_number(phase) >= 5 else 1000.0, "Variation": 200.0 if _phase_number(phase) >= 5 else 0.0, "Hypothèse": "socle ~1 200 € uniquement à la cible"},
        {"Profil": "Indépendant", "Avant": 3000.0, "Après": 3000.0, "Variation": 0.0, "Hypothèse": "pas de barème direct documenté"},
    ]
    df = pd.DataFrame(rows)
    df["Variation %"] = df.apply(lambda r: r["Variation"] / r["Avant"] * 100 if r["Avant"] else 0.0, axis=1)
    st.dataframe(
        df,
        width="stretch",
        hide_index=True,
        column_config={
            "Avant": st.column_config.NumberColumn(format="%.0f €"),
            "Après": st.column_config.NumberColumn(format="%.0f €"),
            "Variation": st.column_config.NumberColumn(format="%+.0f €"),
            "Variation %": st.column_config.NumberColumn(format="%+.1f %%"),
        },
        height=290,
    )
    fig = px.bar(df, x="Profil", y="Variation", title=f"Variation mensuelle directement modélisée — {phase}")
    fig.update_layout(height=310, margin=dict(l=5, r=5, t=45, b=5), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
    st.caption("Repères de revenu : SMIC net juin 2026 (ministère du Travail), salaire médian privé et cadre moyen 2024 (Insee). Le +400 € est l’ordre de grandeur publié par Nouvelle Énergie, pas un barème individuel.")


def _render_methodology(baseline: dict, measures: list[dict]):
    st.markdown("### Méthodologie du simulateur")
    st.caption("Objectif : rendre les ordres de grandeur compréhensibles sans transformer des hypothèses en prévisions.")

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### Ce que le module calcule")
        st.markdown(
            "- effet **mécanique** des économies de dépenses sur le déficit ;\n"
            "- effet mécanique des baisses de prélèvements sur les recettes ;\n"
            "- trajectoire sur cinq ans à **PIB constant** ;\n"
            "- écarts de revenu directement calculables pour quelques profils ;\n"
            "- niveau de vie du ménage en euros annuels par unité de consommation."
        )
    with c2:
        st.markdown("#### Ce qu'il ne prédit pas")
        st.markdown(
            "- croissance future, inflation ou taux d'intérêt ;\n"
            "- créations/destructions d'emplois ;\n"
            "- réactions comportementales des ménages et entreprises ;\n"
            "- rendement macroéconomique futur des baisses d'impôts ;\n"
            "- coûts de transition non documentés."
        )

    st.markdown("#### Formule budgétaire centrale")
    st.code("Déficit simulé = déficit initial − économies de dépenses + baisse des prélèvements actifs + baisse des impôts de production", language="text")
    st.caption("Le déficit est ici affiché comme un montant positif à financer. Une économie le réduit ; une baisse de recette l'augmente mécaniquement.")

    st.markdown("#### Curseur de réalisation")
    st.markdown(
        "Le curseur **Part des économies effectivement réalisées** est un stress-test. "
        "Il réduit uniquement les économies réalisées et laisse les baisses de prélèvements au niveau prévu pour l'horizon choisi. "
        "Il permet donc de voir immédiatement ce qui se passe si les économies sont inférieures à l'objectif. À 100 %, le scénario de référence est inchangé."
    )

    st.markdown("#### Années 2 à 4")
    st.markdown("Les seuls repères temporels utilisés par le module sont 80 Md€ en Année 1 et 200 Md€ à la cible Année 5. Les valeurs 110 / 140 / 170 Md€ des Années 2 à 4 sont une **interpolation linéaire de visualisation**, pas des chiffres publiés.")

    st.markdown("#### Niveau de vie du ménage")
    st.markdown("Le niveau de vie est calculé comme **revenu disponible annuel du ménage / unités de consommation (UC)**. Le module utilise 1 UC pour le premier adulte, 0,5 pour le second adulte et les personnes de 14 ans ou plus, et 0,3 pour les enfants de moins de 14 ans.")

    st.markdown("#### Sources et statuts")
    st.markdown(
        "- **Chiffré par le programme** : repère explicitement publié par Nouvelle Énergie ;\n"
        "- **Donnée publique** : chiffre de référence issu d'une source publique ;\n"
        "- **Calcul / hypothèse** : transformation transparente réalisée par le simulateur ;\n"
        "- **Non chiffré** : mesure affichée mais non intégrée au calcul financier."
    )
    st.markdown(f"**Base France :** [{baseline.get('source_label','Insee')}]({baseline.get('source_url','#')}) — référence {baseline.get('as_of','2025')}.")
    st.markdown("**Programme :** [Nouvelle Énergie — économies](https://www.unenouvelleenergie.fr/questions/quelles-economies-david-lisnard-propose-t-il-et-ou-exactement/) · [Répartition des 200 Md€](https://www.unenouvelleenergie.fr/questions/que-ferait-david-lisnard-des-200-milliards-d-economies/)")
    st.info("Ce simulateur est un outil pédagogique de lecture d'un programme politique. Il ne constitue ni une prévision macroéconomique, ni une simulation fiscale ou de paie individualisée.")

def render_impact_simulator():
    _inject_css()
    baseline = _load_json(BASELINE_PATH, {})
    measures = _load_json(MEASURES_PATH, [])
    if not baseline:
        st.error("Le fichier data/impact_baseline.json est manquant ou illisible.")
        return

    st.markdown("## 🧮 Simulateur d’impact")
    st.markdown(
        '<div class="impact-intro"><b>En pratique :</b> choisissez quand vous voulez regarder l’effet, puis ouvrez <b>France</b> ou <b>Mon foyer</b>. Les détails techniques restent disponibles mais sont repliés.</div>',
        unsafe_allow_html=True,
    )

    try:
        requested_year = int(float(st.query_params.get("year", 5) or 5))
    except Exception:
        requested_year = 5
    requested_year = max(1, min(5, requested_year))
    requested_phase = f"Année {requested_year}"

    st.markdown("### 1. À quel horizon ?")
    if hasattr(st, "segmented_control"):
        phase = st.segmented_control(
            "Horizon",
            options=PHASE_LABELS,
            default=requested_phase,
            key="impact_phase",
            label_visibility="collapsed",
        ) or requested_phase
    else:
        phase = st.radio(
            "Horizon",
            PHASE_LABELS,
            index=requested_year - 1,
            horizontal=True,
            key="impact_phase",
            label_visibility="collapsed",
        )

    if _phase_is_estimated(phase):
        st.caption(f"{phase} est une interpolation de visualisation entre les repères publiés de l’Année 1 et de l’Année 5.")
    else:
        st.caption("Année 1 : premier repère. Année 5 : cible du scénario. Les calculs restent mécaniques et sourcés.")

    st.markdown("### 2. Qu’est-ce que vous voulez voir ?")
    tabs = st.tabs(["🇫🇷 France", "👤 Mon foyer", "👥 Exemples de profils"])
    with tabs[0]:
        _render_france(baseline, measures, phase)
    with tabs[1]:
        _render_you(phase)
    with tabs[2]:
        _render_profiles(phase)

    with st.expander("📚 Sources, hypothèses et méthode", expanded=False):
        st.caption("Cette partie documente les chiffres et les limites du simulateur. Elle n’est pas nécessaire pour une lecture rapide.")
        only_quantified = st.toggle(
            "Afficher uniquement les mesures chiffrées",
            value=False,
            key="impact_only_quantified",
        )
        _render_sources(measures, only_quantified)
        st.divider()
        _render_methodology(baseline, measures)


__all__ = ["render_impact_simulator", "compute_program_scenario", "compute_household_impact", "compute_five_year_trajectory", "_person_direct_impact"]
