# Week 8 - Capstone Project                                       Victor Bagwell
# 140.628.81 Data Science for Public Health in Python
# Covid-19 tracker: daily or cumulative case and death counts for user selected
# countries, from the JHU CSSE Covid-19 time series (Jan 22 2020 - Mar 9 2023).
# Run with: streamlit run capstone.py
# Written with [wAAI Claude Opus 5] AI assistance

import streamlit as st                                                        # web app framework
import pandas as pd                                                           # data frames
import plotly.express as px                                                   # interactive charts

st.set_page_config(page_title="Covid-19 Country Tracker", layout="wide")      # wide page layout

BASE = ("https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/"   # raw data home
        "csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_")  # csv folder

# cumulative counts, one row per date, one column per country
@st.cache_data                                                                # cache the download
def load(measure):
    df = pd.read_csv(BASE + measure + "_global.csv")                          # one csv per measure
    df = df.drop(columns=["Province/State", "Lat", "Long"])                   # keep country, dates
    df = df.groupby("Country/Region").sum()                                   # sum provinces
    df.columns = pd.to_datetime(df.columns, format="%m/%d/%y")                # typed date columns
    return df.T                                                               # dates become rows

# day over day changes; day one keeps its reported count
def to_daily(cum):
    daily = cum.diff()                                                        # day over day change
    daily.iloc[0] = cum.iloc[0]                                               # day one as reported
    return daily                                                              # same shape as input

st.title("Covid-19 Country Tracker")                                          # page heading
st.caption("Historical archive: JHU CSSE time series, Jan 2020 - Mar 2023.")  # archived span

try:                                                                          # downloads can fail
    data = {"Cases": load("confirmed"), "Deaths": load("deaths")}             # both measures once
except Exception:                                                             # any fetch error
    st.error("Could not download the JHU data from GitHub. Rerun to retry.")  # visible message
    st.stop()                                                                 # nothing to show

names = data["Cases"].columns.tolist()                                        # 201 country names
dates = data["Cases"].index                                                   # shared date index

with st.sidebar:                                                              # filters on the left
    st.header("Filters")                                                      # panel title
    countries = st.multiselect("Countries", names, default=["US"])            # add countries
    measure = st.radio("Measure", ["Cases", "Deaths"], horizontal=True)       # what to count
    counts = st.radio("Counts", ["Daily", "Cumulative"], horizontal=True)     # how to count
    average = st.checkbox("Trailing 7-day average",                           # smoothing option
                          disabled=counts == "Cumulative")                    # daily only
    log_y = st.checkbox("Log scale")                                          # axis option
    start, end = st.slider("Dates", min_value=dates[0].date(),                # date range picker
                           max_value=dates[-1].date(),                        # last date in data
                           value=(dates[0].date(), dates[-1].date()))         # whole span default

if not countries:                                                             # empty selection
    st.write("Pick at least one country in the sidebar.")                     # prompt for input
    st.stop()                                                                 # nothing to plot

t0, t1 = pd.Timestamp(start), pd.Timestamp(end)                               # slider as timestamps
full_daily = {m: to_daily(data[m][countries]) for m in data}                  # daily, all dates
daily = {m: full_daily[m].loc[t0:t1] for m in data}                           # inside the dates

cases_n = int(daily["Cases"].sum().sum())                                     # range case total
deaths_n = int(daily["Deaths"].sum().sum())                                   # range death total
peak_n = int(daily["Cases"].sum(axis=1).max())                                # picks combined
cfr = round(deaths_n / cases_n * 100, 2) if cases_n else None                 # per 100 cases

c1, c2, c3, c4 = st.columns(4)                                                # four summary cards
c1.metric("Cases in range", f"{cases_n:,}")                                   # cases card
c2.metric("Deaths in range", f"{deaths_n:,}")                                 # deaths card
c3.metric("Peak daily cases", f"{peak_n:,}")                                  # peak card
c4.metric("Deaths / cases (%)", "n/a" if cfr is None else f"{cfr}")           # n/a when no cases

if counts == "Daily":                                                         # daily view
    shown = full_daily[measure]                                               # before date slice
    if average:                                                               # smoothing on
        shown = shown.rolling(7).mean()                                       # trailing average
    shown = shown.loc[t0:t1]                                                  # now apply dates
else:                                                                         # cumulative view
    shown = data[measure][countries].loc[t0:t1]                               # as reported

long = shown.reset_index(names="date")                                        # index to column
long = long.melt("date", var_name="country", value_name="count")              # long form for px
title = counts + " " + measure.lower()                                        # chart heading
if counts == "Daily" and average:                                             # smoothing shown
    title = title + " - Trailing 7-day average"                               # say so in title
if log_y:                                                                     # log axis shown
    title = title + " - Log scale"                                            # say so in title
fig = px.line(long, x="date", y="count", color="country", log_y=log_y,        # line per country
              title=title)                                                    # heading with options
st.plotly_chart(fig)                                                          # draw the chart
if counts == "Daily":                                                         # notes under chart
    st.caption("Negative daily values are reporting corrections in the "      # corrections note
               "source data, shown as reported.")                             # honest display
    if log_y:                                                                 # log hides values
        st.caption("Log scale cannot show zero or negative daily values.")    # warn about gaps
else:                                                                         # cumulative note
    st.caption("Cumulative counts are totals since Jan 22, 2020. With a "     # life to date
               "restricted date range, the line starts at the total "         # not re-based
               "already reached by the first date shown.")                    # range behavior

fname = "covid_" + counts.lower() + "_" + measure.lower() + ".csv"            # file name to save
st.download_button("Download displayed data (CSV)", shown.to_csv().encode(),  # chart data
                   file_name=fname)                                           # saves as csv

st.subheader("Country comparison")                                            # table section
cases_by = daily["Cases"].sum().astype(int)                                   # per country cases
deaths_by = daily["Deaths"].sum().astype(int)                                 # per country deaths
cfr_by = (deaths_by / cases_by.where(cases_by > 0) * 100).round(2)            # guard zero cases
peak_by = daily["Cases"].max().astype(int)                                    # worst single day
when_by = daily["Cases"].idxmax().apply(lambda t: t.date())                   # date of that peak
table = pd.DataFrame({"Cases": cases_by, "Deaths": deaths_by,                 # assemble table
                      "Deaths / cases (%)": cfr_by,                           # one column per stat
                      "Peak daily cases": peak_by,                            # per country peaks
                      "Peak day": when_by})                                   # display order
dark = [("background-color", "#1f4e79"), ("color", "white")]                  # header colors
mid = [("text-align", "center")]                                              # centered text
box = [("border", "1px solid #cccccc"), ("padding", "4px 12px")]              # cell frame
tidy = [("border-collapse", "collapse")]                                      # single borders
css = [{"selector": "", "props": tidy},                                       # whole table
       {"selector": "th", "props": dark + mid + box},                         # header and names
       {"selector": "td", "props": mid + box}]                                # data cells
table = table.reset_index()                                                   # country as a column
when = daily["Cases"].sum(axis=1).idxmax().date()                             # day of joint peak
total = {"Country/Region": "Total", "Cases": cases_n, "Deaths": deaths_n,     # combined row
         "Deaths / cases (%)": cfr if cfr is not None else float("nan"),      # the card
         "Peak daily cases": peak_n, "Peak day": when}                        # joint peak and day
mean = {"Country/Region": "Mean", "Cases": int(cases_by.mean().round()),      # equal weight
        "Deaths": int(deaths_by.mean().round()),                              # typical country
        "Deaths / cases (%)": round(float(cfr_by.mean()), 2),                 # mean of ratios
        "Peak daily cases": int(peak_by.mean().round()), "Peak day": "N/A"}   # no mean day
rows = pd.DataFrame([total, mean], columns=table.columns)                     # summary rows
table = pd.concat([table, rows], ignore_index=True)                           # append both
style = table.style.format({"Cases": "{:,}", "Deaths": "{:,}",
                            "Peak daily cases": "{:,}",
                            "Deaths / cases (%)": "{:.2f}"},
                           na_rep="")                                         # readable numbers
style = style.set_table_styles(css).hide(axis="index")                        # no row numbers
gray = {"font-weight": "bold", "background-color": "#6b6a66",                 # total band
        "color": "white"}                                                     # white on gray
band = {"font-weight": "bold", "background-color": "#e8eaed",                 # mean band
        "color": "#0b0b0b"}                                                   # dark on light
trow = (table.index[-2:-1], table.columns)                                    # total cells
mrow = (table.index[-1:], table.columns)                                      # mean cells
style = style.set_properties(subset=trow, **gray)                             # darker total row
style = style.set_properties(subset=mrow, **band)                             # lighter mean row
st.markdown(style.to_html(), unsafe_allow_html=True)
st.caption("Counts inside the selected dates.")                               # table note

with st.expander("How to use and data notes"):                                # collapsed notes
    st.write("""
- Pick countries, a measure (cases or deaths), daily or cumulative
  counts, and a date range in the sidebar. The trailing 7-day average
  smooths the daily counts; the log scale helps compare countries of
  very different sizes.
- Daily counts are day-over-day changes in the source's cumulative
  series. Occasional negative days are reporting corrections in the
  source data and are shown as reported, not altered, so totals and
  peak days can reflect reporting revisions as well as new
  infections.
- Cumulative counts are as reported, so a chart that starts mid-range
  starts at the count already reached by that date.
- Deaths / cases (%) is a crude ratio: reported deaths divided by
  reported cases. Deaths lag the cases behind them, so in a short
  date range the two counts are not the same patients. Testing and
  reporting differ by country and over time, so the ratio is not a
  direct measure of severity.
- In the table, the Total row combines the picked countries (total
  deaths over total cases; peak of their summed daily counts). The
  Mean row averages the countries equally, so its ratio can differ
  from the Total row's combined figure.
- Country counts sum the source's province and state rows.
- Recoveries are excluded: JHU stopped collecting them in August 2021.
- Data: JHU CSSE Covid-19 repository on GitHub, a fixed historical
  archive that ends March 9, 2023. This is not a live tracker.
""")
