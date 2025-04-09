### Libraries ###
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
import numpy as np
import datetime
import cx_Oracle

### Page Setup ###
st.set_page_config(
    layout="centered",
    initial_sidebar_state="expanded",
    page_title="Home",
    page_icon='🏭'
)
st.logo('./misc/meyer-logo.png')
## Oracle Connection
host = "mtora11.meyertool.com" 
port = "1521" 
service_name = "mpcs_stby.meyertool.com" 
username = "CPHILLIPPS"
password = 'readonly4887'
dsn_tns = cx_Oracle.makedsn(host, port, service_name=service_name)

### Page Start ###
# Logo
col1, col2, col3 = st.columns(3)
with col2:
    st.image('./misc/meyer-logo.png', use_container_width=True)

# Title
st.title("Quality Reports")
st.divider()

### Data Grab ###
# Set default values
today = datetime.date.today()
yesterday = today - datetime.timedelta(days=1)
day_before_yesterday = today - datetime.timedelta(days=2)
pull_range = yesterday - datetime.timedelta(days=60)

# Date range input with constraints
start_date, end_date = st.date_input(
    "Select date range:",
    [day_before_yesterday, yesterday],  # Default selection
    min_value=pull_range,     # Minimum selectable date
    max_value=yesterday           # Maximum selectable date
)
st.divider()

# Format dates for SQL
start_date_str = start_date.strftime("%d-%b-%Y")
end_date_str = end_date.strftime("%d-%b-%Y")
# SQL query with dynamic date range
query_IA = f"""
SELECT process_plan_id, inspect_type, inspection_id, serial_no,
insp_emp_id, TO_CHAR(date_time, 'DD-MON-YYYY HH24:MI:SS') AS DATE_TIME,
NVL(accept_comment, 'x') AS ACCEPT_COMMENT, NVL(part_program, 'x') AS PART_PROGRAM
FROM inspect.inspect_sum_results
WHERE date_time BETWEEN TO_DATE('{start_date_str}', 'DD-MON-YYYY') 
                    AND TO_DATE('{end_date_str}', 'DD-MON-YYYY')
AND insp_mach_id IN (
    SELECT m.machine_id FROM mpcs.machine m
    WHERE NVL(machine_type, 'x') = 'DEPARTMENT'
)
"""

query_IB = f"""
WITH ranked_ships AS (
    SELECT 
        s.release_no, 
        s.lot_no, 
        s.serial_no, 
        s.resource_no, 
        s.resource_type, 
        ROW_NUMBER() OVER (PARTITION BY s.release_no ORDER BY s.lot_no) AS rn
    FROM mpcs.ship_release_ser s
)
SELECT DISTINCT 
    l.record_user, 
    l.log_comment, 
    r.lot_no, 
    r.serial_no, 
    r.resource_no, 
    r.resource_type, 
    res.resource_name,
    lot.process_plan_id,
    TO_CHAR(l.log_date, 'DD-MON-YYYY') AS log_date
FROM mpcs.mpcs_log l
JOIN ranked_ships r ON r.release_no = REGEXP_SUBSTR(l.log_comment, 'REL: ([0-9]+)', 1, 1, NULL, 1)
JOIN mpcs.lot lot ON r.lot_no = lot.lot_no
JOIN mpcs.part_resource res ON r.resource_no = res.resource_no  
                              AND r.resource_type = res.resource_type  
WHERE l.log_date BETWEEN TO_DATE('{start_date_str}', 'DD-MON-YYYY')  
                    AND TO_DATE('{end_date_str}', 'DD-MON-YYYY')
AND l.table_nm LIKE 'SHIP_RELEASE%'
AND l.screen_nm LIKE 'RELEASE.SQR%'
AND l.log_comment LIKE 'REL%PRINTED%(Acc%)'
AND r.rn = 1
"""

query_MMF = f"""
SELECT process_plan_id, process_step_id, lot_no, serial_no,
accept_emp_id, TO_CHAR(date_time, 'DD-MON-YYYY HH24:MI:SS') AS DATE_TIME,
accept_comments, current_oper_desc, current_part_program,
current_feature_count
FROM mpcs.mfg_process_accept
WHERE date_time BETWEEN TO_DATE('{start_date_str}', 'DD-MON-YYYY') 
                    AND TO_DATE('{end_date_str}', 'DD-MON-YYYY')
"""

## Connection + Pull ##
conn = cx_Oracle.connect(user=username, password=password, dsn=dsn_tns)

# Table 1 - Override on Inspection A #
cursor = conn.cursor()
cursor.execute(query_IA)
rows = cursor.fetchall()
columns = [col[0] for col in cursor.description]
df_IA = pd.DataFrame(rows, columns=columns)
cursor.close()

# Table 2 - Override Inspection B #
cursor = conn.cursor()
cursor.execute(query_IB)
rows = cursor.fetchall()
columns = [col[0] for col in cursor.description]
df_IB = pd.DataFrame(rows, columns=columns)
cursor.close()

# Table 3 - Missing Manufacturing Feature #
cursor = conn.cursor()
cursor.execute(query_MMF)
rows = cursor.fetchall()
columns = [col[0] for col in cursor.description]
df_MMF = pd.DataFrame(rows, columns=columns)
cursor.close()

# Connection close
conn.close()


# Trends
st.subheader("Override Report Trends")
st.text("Show trend of override numbers over the last couple of months/weeks")


# Function to get data from the SQL query
def get_data(query, start_date, end_date):
    conn = cx_Oracle.connect(user=username, password=password, dsn=dsn_tns)
    cursor = conn.cursor()
    query = query.format(start_date_str=start_date, end_date_str=end_date)
    cursor.execute(query)
    rows = cursor.fetchall()
    columns = [col[0] for col in cursor.description]
    df = pd.DataFrame(rows, columns=columns)
    cursor.close()
    return df

# Streamlit UI for selecting options
st.title("Inspection/Release/Acceptance Trends")

# Date input
start_date = st.date_input("Start Date", pd.to_datetime("2025-01-01"))
end_date = st.date_input("End Date", pd.to_datetime("2025-04-01"))

# Granularity selection
granularity = st.selectbox("Select Granularity", ["Daily", "Weekly", "Monthly"])

# Trend Line Toggle
trend_line = st.checkbox("Show Trend Line", value=True)

# Convert dates to strings for query formatting
start_date_str = start_date.strftime("%d-%b-%Y")
end_date_str = end_date.strftime("%d-%b-%Y")

# Fetch data from the respective queries
df_IA = get_data(query_IA, start_date_str, end_date_str)
df_IB = get_data(query_IB, start_date_str, end_date_str)
df_MMF = get_data(query_MMF, start_date_str, end_date_str)

# Ensure DATE_TIME columns are in datetime format
df_IA['DATE_TIME'] = pd.to_datetime(df_IA['DATE_TIME'])
df_IB['log_date'] = pd.to_datetime(df_IB['log_date'])
df_MMF['DATE_TIME'] = pd.to_datetime(df_MMF['DATE_TIME'])

# Resample data based on granularity
if granularity == "Daily":
    df_IA_resampled = df_IA.resample('D', on='DATE_TIME').size()
    df_IB_resampled = df_IB.resample('D', on='log_date').size()
    df_MMF_resampled = df_MMF.resample('D', on='DATE_TIME').size()
elif granularity == "Weekly":
    df_IA_resampled = df_IA.resample('W', on='DATE_TIME').size()
    df_IB_resampled = df_IB.resample('W', on='log_date').size()
    df_MMF_resampled = df_MMF.resample('W', on='DATE_TIME').size()
else:  # Monthly
    df_IA_resampled = df_IA.resample('M', on='DATE_TIME').size()
    df_IB_resampled = df_IB.resample('M', on='log_date').size()
    df_MMF_resampled = df_MMF.resample('M', on='DATE_TIME').size()

# Plot the bar chart for each DataFrame
fig, ax = plt.subplots(figsize=(10, 6))

# Plot for Inspection A
df_IA_resampled.plot(kind='bar', ax=ax, color='skyblue', label='Inspection A', position=0, width=0.25)

# Plot for Inspection B
df_IB_resampled.plot(kind='bar', ax=ax, color='orange', label='Inspection B', position=1, width=0.25)

# Plot for Manufacturing Feature
df_MMF_resampled.plot(kind='bar', ax=ax, color='green', label='Manufacturing Feature', position=2, width=0.25)

# Add a trend line if selected
if trend_line:
    # Adding a simple linear trendline (You can use more sophisticated methods)
    x = np.arange(len(df_IA_resampled))
    y_IA = df_IA_resampled.values
    y_IB = df_IB_resampled.values
    y_MMF = df_MMF_resampled.values

    z_IA = np.polyfit(x, y_IA, 1)
    p_IA = np.poly1d(z_IA)

    z_IB = np.polyfit(x, y_IB, 1)
    p_IB = np.poly1d(z_IB)

    z_MMF = np.polyfit(x, y_MMF, 1)
    p_MMF = np.poly1d(z_MMF)

    ax.plot(df_IA_resampled.index, p_IA(x), color="red", linestyle="--", label="Trend Line (IA)")
    ax.plot(df_IB_resampled.index, p_IB(x), color="purple", linestyle="--", label="Trend Line (IB)")
    ax.plot(df_MMF_resampled.index, p_MMF(x), color="blue", linestyle="--", label="Trend Line (MMF)")

ax.set_title("Total Inspections/Acceptances/Shipments")
ax.set_xlabel("Date")
ax.set_ylabel("Count")
ax.legend()

st.pyplot(fig)