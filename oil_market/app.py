"""Oil market dashboard: how far do IEA, OPEC and EIA demand forecasts diverge?"""
from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st

from src.views import render_evolution, render_gap, render_revisions

PROCESSED = Path(__file__).parent / "data" / "processed" / "agency_forecasts.csv"

st.set_page_config(page_title="Oil forecasts: IEA vs OPEC vs EIA", layout="wide")


@st.cache_data
def load_data(path: str) -> pd.DataFrame:
    df = pd.read_csv(path,
                     dtype={"record_id": str, "agency": str, "report_month": str,
                            "value_basis": str},
                     keep_default_na=False, na_values=[""])
    df["target_year"] = df["target_year"].astype("int64")
    return df


data = load_data(str(PROCESSED))
latest = data["report_month"].max()
lo = date.fromisoformat(data["report_month"].min())
hi = date.fromisoformat(latest)

st.title("Do the world's oil forecasters still agree? IEA vs OPEC vs EIA, 2026")
st.markdown(
    "Each month the IEA, OPEC and the EIA publish a forecast of world oil demand. "
    "This dashboard tracks every monthly **vintage** of those forecasts to show where "
    "the agencies diverge as the 2026 Middle East supply shock unfolded. "
    "Values are transcribed from the agencies' reports as compiled by the IEF; "
    "rows marked *derived* were computed from a reported revision."
)

jan = data[(data["target_year"] == 2026) & (data["report_month"] == "2026-01-01")]
new = data[(data["target_year"] == 2026) & (data["report_month"] == latest)]
if len(jan) and len(new):
    st.info(
        f"2026 growth forecasts spanned {jan['demand_growth_mbd'].max() - jan['demand_growth_mbd'].min():.2f} mb/d "
        f"in the January vintage and {new['demand_growth_mbd'].max() - new['demand_growth_mbd'].min():.2f} mb/d "
        f"across the {len(new)} agencies reporting in the {latest[:7]} vintage "
        f"({', '.join(sorted(new['agency']))})."
    )

render_evolution(data, latest, lo, hi)
render_gap(data, latest)
render_revisions(data, latest, lo, hi)
st.caption("Forecasts are estimates, revised monthly; agencies use different definitions "
           "and baselines, so levels are not strictly comparable.")
