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
#import getpass # Alt: from pwinput import pwinput
# Oracle library
import cx_Oracle
# General Python libaries
import datetime
# Functions
from misc.data_utils import (build_queries, run_query, clean_df_IA, clean_df_IB, clean_df_MMF)


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
pull_range = yesterday - datetime.timedelta(days=120)

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

# Generate queries
query_IA, query_IB, query_MMF = build_queries(start_date_str, end_date_str)

# Connect and fetch data
conn = cx_Oracle.connect(user=username, password=password, dsn=dsn_tns)
df_IA = run_query(conn, query_IA)
df_IB = run_query(conn, query_IB)
df_MMF = run_query(conn, query_MMF)
conn.close()

# Clean up
df_IA = clean_df_IA(df_IA)
df_IB = clean_df_IB(df_IB)
df_MMF = clean_df_MMF(df_MMF)


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
#TODO: Seperate Plan ID and OP to allow for better selection, use columns, also use multiselector
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

# Deep Dive into data'
#TODO: Seperate Plan ID and OP to allow for better selection, use columns, also use multiselector
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

