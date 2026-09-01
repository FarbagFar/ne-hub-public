from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any

import pandas as pd
import plotly.express as px
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
</style>
        """,
        unsafe_allow_html=True,
    )


def _card(label: str, value: str, delta: str = "", good: bool = False, delta_kind: str = "") -> str:
    cls = "impact-card good" if good else "impact-card"
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
) -> dict:
    """Calcul mécanique du scénario agrégé. Aucun effet de croissance n'est appliqué."""
    phase_ratio = _phase_ratio(phase)
    target_savings = 200.0 * phase_ratio
    spending_savings = target_savings if use_spending else 0.0
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

    return {
        "phase_ratio": phase_ratio,
        "target_savings": target_savings,
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
        sc = compute_program_scenario(baseline, phase, use_spending, use_workers, use_production)
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


def _render_allocation_flow(scenario: dict):
    total = float(scenario.get("target_savings", 0.0) or 0.0)
    block = (
        '<div class="impact-strip"><div class="impact-strip-head"><b>Répartition des économies à cet horizon</b>'
        f'<span>{fmt_bn(total)}</span></div><div class="impact-flow">'
        f'<div class="workers">60 % · actifs<br>{fmt_bn(scenario["worker_relief"])}</div>'
        f'<div class="business">20 % · production<br>{fmt_bn(scenario["production_relief"])}</div>'
        f'<div class="balance">20 % · solde<br>{fmt_bn(scenario["deficit_improvement"])}</div>'
        '</div></div>'
    )
    st.markdown(block, unsafe_allow_html=True)


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
    st.dataframe(df, hide_index=True, use_container_width=True, height=min(520, 36*(len(df)+1)), column_config=cfg)
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
    st.dataframe(df, use_container_width=True, hide_index=True, height=min(430, 38 * (len(df) + 1)))


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


def _render_france(baseline: dict, measures: list[dict], phase: str):
    with st.expander("Ajuster le scénario agrégé", expanded=False):
        st.caption("La clé 60/20/20 publiée est activée par défaut. Les options servent uniquement à comprendre la mécanique.")
        c1, c2, c3 = st.columns(3)
        use_spending = c1.toggle("Économies de dépenses", value=True, key=f"impact_spend_{phase}")
        use_workers = c2.toggle("Baisse prélèvements actifs", value=True, key=f"impact_workers_{phase}")
        use_production = c3.toggle("Baisse impôts production", value=True, key=f"impact_prod_{phase}")

    scenario = compute_program_scenario(baseline, phase, use_spending, use_workers, use_production)

    if not (use_spending and use_workers and use_production):
        st.warning("Scénario pédagogique modifié : il ne correspond plus exactement à la clé 60 % / 20 % / 20 % publiée.")

    _cards(
        [
            {"label": "Économies de dépenses", "value": fmt_bn(scenario["spending_savings"]), "delta": "dépenses ↓", "good": True, "delta_kind": "good"},
            {"label": "Prélèvements sur les actifs", "value": fmt_bn(scenario["worker_relief"]), "delta": "prélèvements ↓", "good": True, "delta_kind": "good"},
            {"label": "Impôts de production", "value": fmt_bn(scenario["production_relief"]), "delta": "impôts ↓", "good": True, "delta_kind": "good"},
            {"label": "Amélioration du solde", "value": fmt_bn(scenario["deficit_improvement"], signed=True), "delta": "déficit réduit", "good": True, "delta_kind": "good"},
            {"label": "Déficit simulé", "value": fmt_bn(scenario["deficit_after"]), "delta": f"−{scenario['deficit_improvement']:.1f} Md€", "delta_kind": "good"},
            {"label": "Déficit / PIB", "value": fmt_pct(scenario["deficit_pct_after"]), "delta": f"−{baseline['deficit_pct_gdp']-scenario['deficit_pct_after']:.1f} pt", "delta_kind": "good"},
            {"label": "Dépenses / PIB", "value": fmt_pct(scenario["spending_pct_after"]), "delta": f"−{baseline['spending_pct_gdp']-scenario['spending_pct_after']:.1f} pt", "delta_kind": "good"},
            {"label": "Prélèvements / PIB*", "value": fmt_pct(scenario["po_after"]), "delta": f"−{baseline['mandatory_levies_pct_gdp']-scenario['po_after']:.1f} pt", "delta_kind": "good"},
        ]
    )
    st.caption("* Calcul mécanique à PIB constant. Une baisse de dépense ou de prélèvement apparaît en vert parce qu’elle va dans le sens de l’indicateur affiché ; cela ne préjuge pas des effets macroéconomiques.")

    _render_allocation_flow(scenario)
    _render_progress_to_targets(baseline, scenario)

    export_payload = {
        "horizon": phase,
        "hypothese_intermediaire": _phase_is_estimated(phase),
        "economies_depenses_milliards": round(scenario["spending_savings"], 1),
        "baisse_prelevements_actifs_milliards": round(scenario["worker_relief"], 1),
        "baisse_impots_production_milliards": round(scenario["production_relief"], 1),
        "deficit_initial_milliards": round(scenario["deficit_before"], 1),
        "deficit_simule_milliards": round(scenario["deficit_after"], 1),
        "deficit_pib_pct": round(scenario["deficit_pct_after"], 2),
        "note": "Simulation mécanique à PIB constant ; aucune croissance, inflation ou réaction comportementale n'est intégrée.",
    }
    st.download_button(
        "⬇️ Exporter ce scénario (JSON)",
        data=json.dumps(export_payload, ensure_ascii=False, indent=2),
        file_name=f"scenario_ne_hub_{_phase_number(phase)}.json",
        mime="application/json",
        key=f"impact_export_{phase}",
    )

    if _phase_is_estimated(phase):
        st.warning(f"{phase} : le montant affiché ({scenario['target_savings']:.0f} Md€) est une interpolation linéaire entre 80 Md€ en Année 1 et 200 Md€ en Année 5. Ce montant intermédiaire n'est pas présenté comme un chiffrage officiel.")

    trajectory = compute_five_year_trajectory(baseline, use_spending, use_workers, use_production)
    with st.expander("Voir la trajectoire Années 1 → 5", expanded=True):
        t1, t2 = st.columns([1.45, 1])
        with t1:
            fig_traj = px.line(
                trajectory,
                x="Année",
                y="Déficit (Md€)",
                markers=True,
                title="Déficit mécanique par année",
            )
            fig_traj.update_layout(height=285, margin=dict(l=5, r=5, t=45, b=5), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig_traj, use_container_width=True, config={"displayModeBar": False})
        with t2:
            end = trajectory.iloc[-1]
            st.metric("Déficit Année 1", fmt_bn(float(trajectory.iloc[0]["Déficit (Md€)"])))
            st.metric("Déficit Année 5", fmt_bn(float(end["Déficit (Md€)"])), delta=f"−{baseline['deficit_billion']-float(end['Déficit (Md€)']):.1f} Md€", delta_color="inverse")
            st.metric("Dette évitée sur 5 ans*", fmt_bn(float(end["Écart de dette vs référence (Md€)"])), delta="vs déficit 2025 répété", delta_color="normal")
            st.caption("* Écart mécanique cumulé à PIB constant : ce n'est pas une prévision de dette publique.")
        st.dataframe(
            trajectory[["Année", "Économies (Md€)", "Déficit (Md€)", "Déficit / PIB (%)", "Écart de dette vs référence (Md€)", "Statut"]],
            hide_index=True,
            use_container_width=True,
            height=245,
            column_config={
                "Économies (Md€)": st.column_config.NumberColumn(format="%.0f"),
                "Déficit (Md€)": st.column_config.NumberColumn(format="%.1f"),
                "Déficit / PIB (%)": st.column_config.NumberColumn(format="%.1f %%"),
                "Écart de dette vs référence (Md€)": st.column_config.NumberColumn(format="%.1f"),
            },
        )
        st.caption("Années 2 à 4 : interpolation linéaire de visualisation 110 / 140 / 170 Md€. Année 1 = 80 Md€ ; Année 5 = 200 Md€.")

    a, b = st.columns([1.35, 1])
    with a:
        before_after = pd.DataFrame(
            [
                {"Indicateur": "Déficit", "Avant": scenario["deficit_before"], "Après": scenario["deficit_after"]},
                {"Indicateur": "Dépenses", "Avant": scenario["spending_before"], "Après": scenario["spending_after"]},
                {"Indicateur": "Recettes", "Avant": scenario["revenue_before"], "Après": scenario["revenue_after"]},
            ]
        ).melt(id_vars="Indicateur", var_name="Situation", value_name="Md€")
        fig = px.bar(before_after, x="Indicateur", y="Md€", color="Situation", barmode="group", title="Avant / après — mécanique budgétaire")
        fig.update_layout(height=315, margin=dict(l=5, r=5, t=45, b=5), legend_title_text="", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    with b:
        st.markdown("#### Où en est le solde ?")
        st.metric("Seuil de déficit à 3 % du PIB", fmt_bn(scenario["three_pct_deficit"]))
        st.metric("Écart restant pour atteindre 3 %", fmt_bn(scenario["gap_to_three_pct"]), delta=f"{scenario['deficit_pct_after']-3:.1f} pt au-dessus", delta_color="inverse")
        st.metric("Écart jusqu’à l’équilibre", fmt_bn(scenario["deficit_after"]))
        st.caption("Le seuil de 3 % est utilisé ici comme simple repère budgétaire. Le simulateur ne suppose aucune croissance supplémentaire.")

    with st.expander("Dette à +1 an : garde-fou important", expanded=False):
        d1, d2, d3 = st.columns(3)
        d1.metric("Dette fin 2025", fmt_bn(scenario["debt_before"]))
        d2.metric("Déficit restant", fmt_bn(scenario["deficit_after"]))
        d3.metric("Dette mécanique à +1 an", fmt_bn(scenario["debt_next"]), f"{scenario['debt_next_pct']:.1f} % du PIB")
        st.caption("Tant que le budget reste déficitaire, la dette brute ne diminue pas mécaniquement. Projection à PIB constant, hors ajustements stock-flux et effets macroéconomiques.")

    st.markdown("### Programme en chiffres")
    st.caption("Les lignes détaillées ne sont pas additionnées au scénario de 200 Md€ lorsqu’elles peuvent déjà faire partie de cette enveloppe : cela évite les doubles comptes.")
    _render_program_numbers(measures)
    _render_measure_detail(measures)


def _render_you(phase: str):
    st.markdown("### Votre situation")
    st.caption("Profil anonyme, aucune donnée n’est enregistrée par ce module. Seuls les effets directs documentables sont calculés.")

    c1, c2, c3 = st.columns([1.2, 1, 1])
    profile = c1.selectbox("Profil", ["Salarié", "Famille", "Enseignant", "Retraité", "Indépendant", "Chef d'entreprise"], key="impact_profile")
    monthly_income = c2.number_input("Revenu net / disponible mensuel (€)", min_value=0.0, max_value=100000.0, value=2200.0, step=50.0, key="impact_income")
    salaried_workers = c3.number_input("Actifs salariés concernés", min_value=0, max_value=6, value=2 if profile == "Famille" else (1 if profile in ("Salarié", "Enseignant") else 0), step=1, key="impact_workers_count")

    h1, h2, h3 = st.columns(3)
    adults = h1.number_input("Adultes", 1, 10, 2 if profile == "Famille" else 1, key="impact_adults")
    children_u14 = h2.number_input("Enfants < 14 ans", 0, 10, 1 if profile == "Famille" else 0, key="impact_kids_u14")
    children_14p = h3.number_input("Enfants ≥ 14 ans", 0, 10, 0, key="impact_kids_14p")

    include_salary_relief = profile in ("Salarié", "Famille", "Enseignant")
    at_target = _phase_number(phase) >= 5
    retirement_floor = 1200.0 if profile == "Retraité" and at_target else 0.0
    # +20 % est annoncé en cinq ans, mais aucune cadence annuelle n'est publiée dans la source utilisée.
    # Pour éviter d'inventer un calendrier, l'effet enseignant n'est appliqué qu'en Année 5.
    teacher_raise_pct = 20.0 if profile == "Enseignant" and at_target else 0.0

    result = compute_household_impact(
        monthly_income=monthly_income,
        salaried_workers=int(salaried_workers),
        adults=int(adults),
        children_u14=int(children_u14),
        children_14p=int(children_14p),
        phase=phase,
        include_salary_relief=include_salary_relief,
        retirement_floor=retirement_floor,
        teacher_raise_pct=teacher_raise_pct,
    )

    change_pct = (result["after"] / monthly_income - 1) * 100 if monthly_income else None
    living_pct = (result["living_after"] / result["living_before"] - 1) * 100 if result["living_before"] else None

    _cards(
        [
            {"label": "Revenu avant", "value": fmt_eur(monthly_income)},
            {"label": "Variation directe", "value": fmt_eur(result["change"], signed=True), "delta": fmt_eur(result["change"] * 12, signed=True) + "/an", "good": result["change"] > 0, "delta_kind": "good" if result["change"] > 0 else ""},
            {"label": "Revenu après", "value": fmt_eur(result["after"]), "delta": fmt_pct(change_pct, signed=True) if change_pct is not None else "—", "good": result["change"] > 0, "delta_kind": "good" if result["change"] > 0 else ""},
            {"label": "Niveau de vie / UC", "value": fmt_eur(result["living_after"]), "delta": fmt_pct(living_pct, signed=True) if living_pct is not None else "—", "good": result["change"] > 0, "delta_kind": "good" if result["change"] > 0 else ""},
        ]
    )

    breakdown = []
    if result["salary_gain"]:
        breakdown.append({"Effet direct": "Baisse des prélèvements sur le travail", "Mensuel": result["salary_gain"], "Statut": "Ordre de grandeur du programme"})
    if result["teacher_gain"]:
        breakdown.append({"Effet direct": "Revalorisation enseignant +20 %", "Mensuel": result["teacher_gain"], "Statut": "Calcul mécanique à la cible"})
    if result["retirement_gain"]:
        breakdown.append({"Effet direct": "Écart vers le socle retraite ~1 200 €", "Mensuel": result["retirement_gain"], "Statut": "Calcul mécanique à la cible"})
    if breakdown:
        bdf = pd.DataFrame(breakdown)
        st.dataframe(bdf, hide_index=True, use_container_width=True, column_config={"Mensuel": st.column_config.NumberColumn(format="%+.0f €")})
    else:
        st.info("Aucun effet monétaire direct suffisamment documenté n’est appliqué automatiquement à ce profil pour cet horizon.")

    if include_salary_relief:
        gain_per_worker = 400.0 * _phase_ratio(phase)
        if _phase_is_estimated(phase):
            ratio_text = f"{gain_per_worker:.0f} € par actif salarié : interpolation linéaire de visualisation, non publiée par le programme"
        elif _phase_number(phase) == 1:
            ratio_text = "160 € par actif salarié en Année 1 (hypothèse proportionnelle 80/200)"
        else:
            ratio_text = "presque 400 € nets par salarié en Année 5, ordre de grandeur publié"
        st.caption(f"Salaire net : {ratio_text}. Ce n’est pas un bulletin de paie ; aucun barème détaillé de cotisations n’est disponible dans la source utilisée.")
    if profile == "Enseignant" and _phase_number(phase) < 5:
        st.warning("Le programme annonce +20 % de rémunération en cinq ans mais ne publie pas ici la cadence annuelle. L'effet n'est donc appliqué automatiquement qu'en Année 5.")
    if profile == "Retraité":
        st.caption("Pour la cible, le calcul utilise la page Questions mise à jour en août 2026 indiquant un socle autour de 1 200 €. Une page de programme plus ancienne mentionne aussi un minimum-vieillesse à 1 000 € : ces formulations ne sont pas identiques, donc l’hypothèse est signalée.")

    if profile == "Chef d'entreprise":
        st.markdown("### Entreprise")
        p1, p2 = st.columns(2)
        profit = p1.number_input("Bénéfice imposable (€)", min_value=0.0, max_value=1_000_000_000.0, value=200000.0, step=10000.0, key="impact_profit")
        local_rate = p2.slider("Part locale hypothétique de l’IS", 0.0, 5.0, 2.5, 0.5, key="impact_local_is")
        current_is = profit * 0.25
        target_rate = 0.20 + local_rate / 100.0
        target_is = profit * target_rate
        _cards([
            {"label": "IS au taux normal 25 %", "value": fmt_eur(current_is)},
            {"label": "IS simulé", "value": fmt_eur(target_is), "delta": f"taux {target_rate*100:.1f} %"},
            {"label": "Écart d’IS", "value": fmt_eur(current_is-target_is, signed=True), "delta": "charge fiscale ↓" if target_is < current_is else "", "good": target_is < current_is, "delta_kind": "good" if target_is < current_is else ""},
            {"label": "Bénéfice après IS", "value": fmt_eur(profit-target_is)},
        ])
        st.caption("Calcul simplifié : hors taux PME à 15 %, assiette fiscale, crédits d’impôt, déficits reportables et contributions additionnelles. La part locale de 0 à 5 % reste une hypothèse utilisateur.")


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
        use_container_width=True,
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
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    st.caption("Repères de revenu : SMIC net juin 2026 (ministère du Travail), salaire médian privé et cadre moyen 2024 (Insee). Le +400 € est l’ordre de grandeur publié par Nouvelle Énergie, pas un barème individuel.")


def render_impact_simulator():
    _inject_css()
    baseline = _load_json(BASELINE_PATH, {})
    measures = _load_json(MEASURES_PATH, [])
    if not baseline:
        st.error("Le fichier data/impact_baseline.json est manquant ou illisible.")
        return

    st.markdown("## 🧮 Simulateur d’impact")
    st.markdown(
        '<div class="impact-intro">Voir concrètement ce que changent les mesures chiffrées : comptes publics, revenu disponible et profils-types. Chaque résultat indique ce qui vient du programme, d’une donnée publique ou d’une hypothèse de calcul.</div>',
        unsafe_allow_html=True,
    )

    top1, top2, top3 = st.columns([1.15, 2.1, 1.05])
    with top1:
        if hasattr(st, "segmented_control"):
            phase = st.segmented_control(
                "Horizon",
                options=PHASE_LABELS,
                default="Année 5",
                key="impact_phase",
            )
            if phase is None:
                phase = "Année 5"
        else:
            phase = st.radio(
                "Horizon",
                PHASE_LABELS,
                index=4,
                horizontal=True,
                key="impact_phase",
            )
    with top2:
        if _phase_is_estimated(phase):
            st.caption(f"{phase} = interpolation linéaire entre 80 Md€ en Année 1 et 200 Md€ en Année 5. Aucune croissance supplémentaire n’est supposée.")
        else:
            st.caption("Année 1 = 80 Md€ annoncés. Année 5 = cible de 200 Md€. Années 2 à 4 = hypothèses linéaires clairement signalées.")
    with top3:
        only_quantified = st.toggle("Chiffré uniquement", value=False, key="impact_only_quantified", help="Masque dans les tableaux les mesures sans repère chiffré explicite.")

    shown_measures = [m for m in measures if (not only_quantified or _quantified_measure(m))]
    stats = _measure_summary(measures)
    st.markdown(
        f'<div class="impact-source-row"><span class="impact-source-pill">{stats["total"]} mesures / objectifs suivis</span>'
        f'<span class="impact-source-pill">{stats["quantified"]} avec repère chiffré</span>'
        f'<span class="impact-source-pill">{stats["modeled"]} à effet direct modélisé</span></div>',
        unsafe_allow_html=True,
    )

    tabs = st.tabs(["🇫🇷 France", "👤 Vous", "👥 Profils", "📚 Sources"])
    with tabs[0]:
        _render_france(baseline, shown_measures, phase)
    with tabs[1]:
        _render_you(phase)
    with tabs[2]:
        _render_profiles(phase)
    with tabs[3]:
        _render_sources(measures, only_quantified)

    with st.expander("Méthodologie, sources et limites", expanded=False):
        st.markdown(
            "**Lecture des statuts** : 🟢 chiffre publié par le programme ; 🔵 donnée publique ; 🟠 calcul ou hypothèse transparente ; ⚪ non chiffré.\n\n"
            "Le scénario agrégé n’additionne pas les sous-mesures susceptibles d’être déjà comprises dans les 200 Md€ afin d’éviter les doubles comptes. "
            "Les Années 2 à 4 utilisent une interpolation linéaire transparente (110 / 140 / 170 Md€) entre 80 Md€ en Année 1 et 200 Md€ en Année 5 ; ce ne sont pas des montants publiés. "
            "Sont exclus par défaut : croissance, emploi, inflation, réactions comportementales, rendement futur de la capitalisation, fiscalité complète des ménages et coûts de transition non documentés."
        )
        st.markdown(f"**Base France :** [{baseline.get('source_label','Insee')}]({baseline.get('source_url','#')}) — référence {baseline.get('as_of','2025')}.")
        st.markdown("**Source programme principale :** [Nouvelle Énergie — Quelles économies ?](https://www.unenouvelleenergie.fr/questions/quelles-economies-david-lisnard-propose-t-il-et-ou-exactement/) · [Répartition des 200 Md€](https://www.unenouvelleenergie.fr/questions/que-ferait-david-lisnard-des-200-milliards-d-economies/)")


__all__ = ["render_impact_simulator", "compute_program_scenario", "compute_household_impact", "compute_five_year_trajectory"]
