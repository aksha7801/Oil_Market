# Oil market: do IEA, OPEC and EIA still agree?

**Question:** How well do the IEA, OPEC and EIA estimates of 2026 world oil demand agree, and where and when did they diverge as the 2026 Middle East supply shock unfolded?

**Audience:** energy analysts and policy staff who need to know which forecast to trust and how wide the uncertainty is.

**Finding (from the data):** in January 2026 the three agencies' 2026 demand-growth forecasts spanned 0.5 mb/d (OPEC +1.4, EIA +1.1, IEA +0.9). By the October vintage OPEC still expected growth (+0.2) while the IEA expected a 2.6 mb/d fall, a gap of 2.8 mb/d. Forecasts for 2027 converge on a 2.0-2.6 mb/d rebound.

## Views
1. `forecast_evolution` - monthly vintages of each agency's growth forecast.
2. `agency_gap` - highest-minus-lowest gap by report month, for growth or level.
3. `revision_tracker` - cumulative revision of each 2026 forecast against a chosen baseline.

## Data and provenance
`data/sample/agency_forecasts.csv` has 34 rows (3 agencies x report months Jan-Oct 2026 for 2026, plus Sep-Oct 2026 for 2027). Values were transcribed on 26 Oct 2026 from the IEF *Comparative Analysis* summaries of the IEA OMR, OPEC MOMR and EIA STEO, cross-checked against the OPEC (Oct 2026), IEA (Sep/Oct 2026) report coverage. Limits: EIA October 2026 is missing; IEA Aug and EIA Aug 2026 are `derived` from the revision stated in the September compilation; Feb IEA and several levels are blank because they were not reported. Not a substitute for the agencies' own tables.

## Run
```bash
pip install -r requirements.txt
streamlit run app.py
python src/data.py --mode offline   # rebuild processed file from sample (offline)
python src/data.py --mode live      # merge data/raw/new_vintages.csv (same columns) then rebuild
```
Python 3.11.

## Not yet covered
Prices, inventories and trade flows from the other listed sources are not used.
