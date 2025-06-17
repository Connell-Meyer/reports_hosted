### Libraries ###
import pandas as pd
import streamlit as st
import plotly.express as px
import datetime
from misc.data_utils import build_summary_queries, run_query, get_oracle_connection

### Page Setup ###
st.set_page_config(
    layout="wide",
    initial_sidebar_state="expanded",
    page_title="Home",
    page_icon='🏭',
)

### Page Start ###
# Logo
col1, col2, col3 = st.columns(3)
with col2:
    st.image('./misc/meyer-logo.png', width=300)  # Set width in pixels
    st.title("Dashboard")


# Override report summary
st.divider()
st.subheader("Override Trend")


# Date range and granularity selection
today = datetime.date.today()
default_start = datetime.date(today.year, 1, 1)
c1, c2 = st.columns(2)
with c1:
    start_date, end_date = st.date_input("Select Date Range", [default_start, today])
with c2:
    granularity = st.selectbox("Select Granularity", ["Daily", "Weekly", "Monthly"], index=1)

# Adjust end_date to exclude current partial cycle
if granularity == "Daily":
    adjusted_end = end_date - datetime.timedelta(days=1)

elif granularity == "Weekly":
    weekday = end_date.weekday()  # Monday = 0
    adjusted_end = end_date - datetime.timedelta(days=weekday)  # Go to previous Monday

elif granularity == "Monthly":
    adjusted_end = end_date.replace(day=1) - datetime.timedelta(days=1)  # Last day of previous month

else:
    adjusted_end = end_date

# Format for Oracle
start_str = start_date.strftime("%d-%b-%Y")
end_str = adjusted_end.strftime("%d-%b-%Y")

# Query data
query_IA_sum, query_IB_sum, query_MMF_sum = build_summary_queries(start_str, end_str, granularity)
conn = get_oracle_connection()
df_IA = run_query(conn, query_IA_sum)
df_IB = run_query(conn, query_IB_sum)
df_MMF = run_query(conn, query_MMF_sum)
conn.close()

# Add source labels
df_IA['SOURCE'] = 'Inspection Override'
df_IB['SOURCE'] = 'Audit Program Override'
df_MMF['SOURCE'] = 'Missing Manufaturing Feature'

# Combine all into one DataFrame
df_all = pd.concat([df_IA, df_IB, df_MMF], ignore_index=True)

# Convert EVENT_DATE based on granularity
if granularity == "Weekly":
    df_all['EVENT_DATE'] = pd.to_datetime(df_all['EVENT_DATE'] + '-1', format='%G-%V-%u', errors='coerce')
else:
    df_all['EVENT_DATE'] = pd.to_datetime(df_all['EVENT_DATE'], errors='coerce', infer_datetime_format=True)

# Drop rows with invalid EVENT_DATE
df_all.dropna(subset=['EVENT_DATE'], inplace=True)

# Plot
fig = px.line(
    df_all,
    x='EVENT_DATE',
    y='COUNT',
    color='SOURCE',
    title='Override Counts Over Time'
)

st.plotly_chart(fig, use_container_width=True)
###
st.divider()
