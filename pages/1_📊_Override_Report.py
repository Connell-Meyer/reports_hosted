### Inizializtion Imports ###
# Standard DS libraries
import pandas as pd
import numpy as np
# Visualization libraries
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px
import plotly.graph_objects as go
# Streamlit
import streamlit as st
# Secrity
import getpass # Alt: from pwinput import pwinput
# Oracle library
import cx_Oracle
# General Python libaries
import datetime


### Page Setup ###
st.set_page_config(
    layout="centered",
    initial_sidebar_state="expanded",
    page_title='Override Report',
    page_icon='📊'
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
st.title("Override Report")
st.divider()

## Data Pull ##
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

## Data Clean ##
# df_IA
cat_cols = ['PROCESS_PLAN_ID', 'INSPECT_TYPE', 'INSPECTION_ID', 'SERIAL_NO', 'INSP_EMP_ID', 'PART_PROGRAM']
date_time_cols = ['DATE_TIME']    
object_cols = ['ACCEPT_COMMENT']
df_IA[cat_cols] = df_IA[cat_cols].astype('category')
df_IA[date_time_cols] = df_IA[date_time_cols].apply(pd.to_datetime, format="mixed")
df_IA[object_cols] = df_IA[object_cols].astype('object')

# df_IB
df_IB['RELEASE_NUMBER'] = df_IB['LOG_COMMENT'].str.extract(r'REL: (\d+)')
df_IB['ACCEPTED'] = df_IB['LOG_COMMENT'].str.extract(r'Accepted: (\d+)').astype(int)
df_IB['TOTAL'] = df_IB['LOG_COMMENT'].str.extract(r'Out of: (\d+)').astype(int)
df_IB['PROGRAM'] = df_IB['LOG_COMMENT'].str.extract(r'sampling not enough for: (.*?);?\)')
df_IB['RELEASE_NUMBER'] = df_IB['RELEASE_NUMBER'].astype(int)
df_IB = df_IB.drop(columns=['LOG_COMMENT'])
cat_cols = ['RECORD_USER', 'RELEASE_NUMBER', 'PROGRAM']
df_IB[cat_cols] = df_IB[cat_cols].astype('category')

# df_MMF
df_MMF['OP'] = df_MMF['CURRENT_OPER_DESC'].str.extract(r'^(\d+)')
df_MMF['OP_DESC'] = df_MMF['CURRENT_OPER_DESC'].str.extract(r'^\d+\s*-\s*(.*)')
df_MMF[['VANE', 'LOOP_CNT', 'REQD_FEATURES', 'TOTAL']] = df_MMF['CURRENT_FEATURE_COUNT'].str.extract(
    r'VANE: (\d+) - LOOP CNT: (\d+) - REQRD FEATURES: (\d+) - TOTAL: (\d+)'
)
df_MMF[['VANE', 'LOOP_CNT', 'REQD_FEATURES', 'TOTAL']] = df_MMF[['VANE', 'LOOP_CNT', 'REQD_FEATURES', 'TOTAL']].apply(pd.to_numeric)
df_MMF.drop(columns = ['CURRENT_OPER_DESC', 'CURRENT_FEATURE_COUNT'], inplace=True)
cat_cols = ['PROCESS_PLAN_ID', 'PROCESS_STEP_ID', 'LOT_NO', 'SERIAL_NO', 'ACCEPT_EMP_ID', 'CURRENT_PART_PROGRAM', 'OP']
date_time_cols = ['DATE_TIME']    
object_cols = ['ACCEPT_COMMENTS', 'OP_DESC']
df_MMF[cat_cols] = df_MMF[cat_cols].astype('category')
df_MMF[date_time_cols] = df_MMF[date_time_cols].apply(pd.to_datetime, format="mixed")
df_MMF[object_cols] = df_MMF[object_cols].astype('object')


### Plotting ###
## Missing Manufacturing Feature Override ##
st.subheader("Missing Manufacturing Feature Report:")
# Count occurrences of each (PROCESS_PLAN_ID, OP) pair
df_count_MMF = df_MMF.groupby(['PROCESS_PLAN_ID', 'OP'], observed=True).size().reset_index(name='Count')

# Sort by count in descending order and select the top 20
df_top10_MMF = df_count_MMF.sort_values(by='Count', ascending=False).head(20)

# Create a formatted column for x-axis labels
df_top10_MMF['PLAN_OP'] = df_top10_MMF['PROCESS_PLAN_ID'].astype(str) + " - OP " + df_top10_MMF['OP'].astype(str)

# Create the bar chart (with enforced order)
fig_MMF = px.bar(df_top10_MMF, 
             x='PLAN_OP',  # Use the formatted column for x-axis
             y='Count', 
             color='PROCESS_PLAN_ID', 
             text='Count',
             title="Top 10 Most Frequent PROCESS_PLAN_ID and OP Combinations",
             labels={"PLAN_OP": "PROCESS_PLAN_ID - OP", "Count": "Number of Overrides"},
             hover_data={'PROCESS_PLAN_ID': True, 'OP': True, 'Count': True, 'PLAN_OP': False},
             category_orders={"PLAN_OP": df_top10_MMF['PLAN_OP'].tolist()}  # Enforce sorted order
             )

# Improve x-axis readability
fig_MMF.update_layout(
    xaxis=dict(
        tickangle=-45  # Rotates the labels for better readability
    ),
    xaxis_title="PROCESS_PLAN_ID - OP",
    yaxis_title="Count",
    bargap=0.2,
    width=1000,  # Increase width for better spacing
    height=500
)

fig_MMF.update_traces(textposition='outside')
st.plotly_chart(fig_MMF, use_container_width=True)

# Deep Dive into data
with st.form('MMF_Deep_Dive'):
    selected_plan_op_MMF = st.selectbox("Select a Process Plan ID and OP combination", df_top10_MMF['PLAN_OP'])
    MMF_submit = st.form_submit_button('Submit')
    if MMF_submit:
        selected_plan_id_MMF, selected_op_MMF = selected_plan_op_MMF.split(" - OP ")
        selected_plan_id_MMF = int(selected_plan_id_MMF)
        selected_op_MMF = str(selected_op_MMF)

        # Filter the original dataframe
        filtered_df_MMF = df_MMF[(df_MMF['PROCESS_PLAN_ID'] == selected_plan_id_MMF) & (df_MMF['OP'] == selected_op_MMF)]

        # Display filtered data
        st.write(f"### Entries for {selected_plan_id_MMF} - OP {selected_op_MMF}:")
        st.dataframe(filtered_df_MMF)

## Override Inspection A ##
st.divider()
st.subheader("Override on Inspection Report:")

# Count occurrences of each (PROCESS_PLAN_ID, PART_PROGRAM) pair
df_count_IA = df_IA.groupby(['PROCESS_PLAN_ID', 'PART_PROGRAM'], observed=True).size().reset_index(name='Count')

# Sort by count in descending order and select the top 20
df_top10_IA = df_count_IA.sort_values(by='Count', ascending=False).head(20)

# Create a formatted column for x-axis labels
df_top10_IA['PLAN_PROGRAM'] = df_top10_IA['PROCESS_PLAN_ID'].astype(str) + " - " + df_top10_IA['PART_PROGRAM'].astype(str)

# Create the bar chart (with enforced order)
fig_IA = px.bar(df_top10_IA,  # ✅ Corrected DataFrame reference
             x='PLAN_PROGRAM',  # Use the formatted column for x-axis
             y='Count', 
             color='PROCESS_PLAN_ID', 
             text='Count',
             title="Top 10 Most Frequent PROCESS_PLAN_ID and PROGRAM Combinations",
             labels={"PLAN_PROGRAM": "PROCESS_PLAN_ID - PROGRAM", "Count": "Number of Overrides"},
             hover_data={'PROCESS_PLAN_ID': True, 'PART_PROGRAM': True, 'Count': True, 'PLAN_PROGRAM': False},  # ✅ Fixed column name
             category_orders={"PLAN_PROGRAM": df_top10_IA['PLAN_PROGRAM'].tolist()}  # ✅ Corrected DataFrame reference
             )

# Improve x-axis readability
fig_IA.update_layout(
    xaxis=dict(
        tickangle=-45  # Rotates the labels for better readability
    ),
    xaxis_title="PROCESS_PLAN_ID - PROGRAM",
    yaxis_title="Count",
    bargap=0.2,
    width=1000,  # Increase width for better spacing
    height=500
)

fig_IA.update_traces(textposition='outside')
st.plotly_chart(fig_IA, use_container_width=True)

# Deep Dive into data
with st.form('IA_Deep_Dive'):
    selected_plan_program_IA = st.selectbox("Select a Process Plan ID and PROGRAM combination", df_top10_IA['PLAN_PROGRAM'])
    IA_submit = st.form_submit_button('Submit')
    if IA_submit:
        selected_plan_id_IA, selected_program_IA = selected_plan_program_IA.split(" - ")
        selected_plan_id_IA = int(selected_plan_id_IA)
        selected_program_IA = str(selected_program_IA)

        # Filter the original dataframe
        filtered_df_IA = df_IA[(df_IA['PROCESS_PLAN_ID'] == selected_plan_id_IA) & (df_IA['PART_PROGRAM'] == selected_program_IA)]

        # Display filtered data
        st.write(f"### Entries for {selected_plan_id_IA} - {selected_program_IA}:")
        st.dataframe(filtered_df_IA)

## Override Inspection B ##
st.divider()

