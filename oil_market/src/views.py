"""Streamlit view renderers for the oil_market dashboard."""
from __future__ import annotations

from datetime import date

import altair as alt
import pandas as pd
import streamlit as st

SOURCES = [
    ("International Energy Forum (IEF)",
     "Comparative Analysis of Monthly Reports on the Oil Market"),
    ("International Energy Agency (IEA)", "Oil Market Report"),
    ("Organization of the Petroleum Exporting Countries (OPEC)",
     "Monthly Oil Market Report"),
    ("U.S. Energy Information Administration (EIA)", "Short-Term Energy Outlook"),
]
AGENCIES = ["IEA", "OPEC", "EIA"]
YEARS = [2026, 2027]
NO_DATA = "No forecasts match the current selection. Widen the filters to see results."


def to_iso(d: date) -> str:
    return d.isoformat()


def attribution(latest: str) -> None:
    st.caption("Sources: " + "; ".join(f"{t} ({p})" for p, t in SOURCES) + ".")
    st.caption(f"Latest observation: {latest} (report month of the newest vintage).")


def csv_download(df: pd.DataFrame, key: str) -> None:
    # Always rendered and enabled: when the selection is empty it is header-only.
    st.download_button(
        "Download filtered forecasts (CSV)",
        data=df.to_csv(index=False).encode("utf-8"),
        file_name="oil_agency_forecasts_filtered.csv",
        mime="text/csv",
        key=key,
    )


def _apply(df, agencies, year=None, start=None, end=None):
    out = df[df["agency"].isin(agencies)]
    if year is not None:
        out = out[out["target_year"] == year]
    if start is not None:
        out = out[(out["report_month"] >= to_iso(start)) & (out["report_month"] <= to_iso(end))]
    return out


def _line(df, y, ytitle):
    df = df.assign(report_date=pd.to_datetime(df["report_month"]))
    return (alt.Chart(df).mark_line(point=True)
            .encode(x=alt.X("report_date:T", title="Report month (vintage)"),
                    y=alt.Y(f"{y}:Q", title=ytitle),
                    color=alt.Color("agency:N", title="Agency"),
                    tooltip=["agency", "report_month", y])
            .properties(height=320))


def render_evolution(data: pd.DataFrame, latest: str, lo: date, hi: date) -> None:
    with st.container(key="forecast_evolution"):
        st.subheader("How each agency's demand-growth forecast evolved")
        st.caption("Unit: million barrels per day (mb/d), year-on-year change in world oil demand.")
        attribution(latest)
        agencies = st.multiselect("Agencies", AGENCIES, default=AGENCIES, key="fe_agencies")
        year = st.selectbox("Forecast year", YEARS, index=0, key="fe_year")
        start, end = st.slider("Report months", min_value=lo, max_value=hi,
                               value=(lo, hi), format="YYYY-MM", key="fe_period")
        sel = _apply(data, agencies, year, start, end)
        if sel.empty:
            st.info(NO_DATA)
        else:
            newest = sel[sel["report_month"] == sel["report_month"].max()]
            spread = newest["demand_growth_mbd"].max() - newest["demand_growth_mbd"].min()
            st.metric(f"Spread between agencies, {newest['report_month'].iloc[0][:7]} vintage (mb/d)",
                      f"{spread:.2f}")
            st.altair_chart(_line(sel, "demand_growth_mbd", f"{year} demand growth (mb/d)"),
                            use_container_width=True)
            st.dataframe(sel, use_container_width=True, hide_index=True)
        csv_download(sel, "fe_download")


def render_gap(data: pd.DataFrame, latest: str) -> None:
    with st.container(key="agency_gap"):
        st.subheader("Gap between the highest and lowest agency forecast")
        st.caption("Unit: mb/d. Gap = highest minus lowest value among selected agencies, per report month.")
        attribution(latest)
        agencies = st.multiselect("Agencies", AGENCIES, default=AGENCIES, key="gap_agencies")
        year = st.selectbox("Forecast year", YEARS, index=0, key="gap_year")
        measure = st.radio("Measure", ["Growth (mb/d y/y)", "Level (mb/d)"], key="gap_measure")
        sel = _apply(data, agencies, year)
        col = "demand_growth_mbd" if measure.startswith("Growth") else "demand_level_mbd"
        if sel.empty:
            st.info(NO_DATA)
        else:
            if len(agencies) < 2:
                st.caption("Select at least two agencies for a meaningful gap.")
            g = (sel.dropna(subset=[col]).groupby("report_month")[col]
                 .agg(highest="max", lowest="min", n="count").reset_index())
            g = g[g["n"] >= 2]
            g["gap_mbd"] = (g["highest"] - g["lowest"]).round(2)
            if g.empty:
                st.caption("Fewer than two agencies reported this measure in any month.")
            else:
                top = g.loc[g["gap_mbd"].idxmax()]
                st.metric(f"Widest gap ({top['report_month'][:7]} vintage, mb/d)", f"{top['gap_mbd']:.2f}")
                chart = (alt.Chart(g).mark_bar()
                         .encode(x=alt.X("report_month:O", title="Report month (vintage)"),
                                 y=alt.Y("gap_mbd:Q", title="Gap (mb/d)"),
                                 tooltip=["report_month", "highest", "lowest", "gap_mbd"])
                         .properties(height=320))
                st.altair_chart(chart, use_container_width=True)
                st.table(g.drop(columns="n").set_index("report_month"))
        csv_download(sel, "gap_download")


def render_revisions(data: pd.DataFrame, latest: str, lo: date, hi: date) -> None:
    with st.container(key="revision_tracker"):
        st.subheader("How far each agency has revised its 2026 forecast")
        st.caption("Unit: mb/d change in the 2026 growth forecast relative to the chosen baseline vintage.")
        attribution(latest)
        agencies = st.multiselect("Agencies", AGENCIES, default=AGENCIES, key="rev_agencies")
        start, end = st.slider("Report months", min_value=lo, max_value=hi,
                               value=(lo, hi), format="YYYY-MM", key="rev_period")
        months = sorted(data.loc[data["target_year"] == 2026, "report_month"].unique())
        baseline = st.selectbox("Baseline vintage", months, index=0, key="rev_baseline")
        sel = _apply(data, agencies, None, start, end)
        if sel.empty:
            st.info(NO_DATA)
        else:
            s26 = sel[sel["target_year"] == 2026]
            base_month = max(baseline, s26["report_month"].min())
            base = (s26[s26["report_month"] == base_month]
                    .set_index("agency")["demand_growth_mbd"].rename("base"))
            r = s26[s26["report_month"] >= base_month].join(base, on="agency").dropna(subset=["base"])
            r = r.assign(revision_mbd=(r["demand_growth_mbd"] - r["base"]).round(2))
            if r.empty:
                st.caption("The chosen baseline has no forecasts for the selected agencies.")
            else:
                last = r[r["report_month"] == r.groupby("agency")["report_month"].transform("max")]
                big = last.loc[last["revision_mbd"].abs().idxmax()]
                st.metric(f"Largest revision since {base_month[:7]}: {big['agency']} (mb/d)",
                          f"{big['revision_mbd']:+.2f}")
                st.altair_chart(_line(r, "revision_mbd", "Revision vs baseline (mb/d)"),
                                use_container_width=True)
                st.dataframe(r[["agency", "report_month", "demand_growth_mbd", "revision_mbd"]],
                             use_container_width=True, hide_index=True)
        csv_download(sel, "rev_download")
