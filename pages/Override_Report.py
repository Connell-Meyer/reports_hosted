# Standard DS libraries
import pandas as pd
import numpy as np

# Visualization libraries
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px

# Streamlit
import streamlit as st

# Secrity
import getpass # Alt: from pwinput import pwinput

# Oracle Library
import cx_Oracle


### Page Start ###
st.set_page_config(page_title="Override Report")
st.title("Override Report")
st.divider()

### Data Import Selection
# Define connection details
host = "mtora11.meyertool.com" 
port = "1521" 
service_name = "mpcs_stby.meyertool.com" 
username = "CPHILLIPPS"
password = 'readonly4887'
#password = getpass.getpass('Password:') # Alt: password = pwinput.pwinput(prompt='Password: ', mask='*')

# Create a Data Source Name (DSN)
dsn_tns = cx_Oracle.makedsn(host, port, service_name=service_name)

# Establish connection
conn = cx_Oracle.connect(user=username, password=password, dsn=dsn_tns)
print("Connected to Oracle Database!")
### Table 1 - Override on Inspection A

# Create a cursor object
cursor = conn.cursor()

# Define SQL query (modify table name accordingly)
query = """
select process_plan_id, inspect_type, inspection_id, serial_no,
   insp_emp_id, to_char(date_time,'DD-MON-YYYY HH24:MI:SS') as DATE_TIME,
   nvl(accept_comment,'x') as ACCEPT_COMMENT, nvl(part_program,'x') AS PART_PROGRAM
from inspect.inspect_sum_results
where date_time between trunc(sysdate-1) and trunc(sysdate)
  and insp_mach_id in
      (select m.machine_id from mpcs.machine m
       where nvl(machine_type,'x') = 'DEPARTMENT')
"""

# Execute the query
cursor.execute(query)

# Fetch all rows from the result
rows = cursor.fetchall()
    
# Get column names from cursor description
columns = [col[0] for col in cursor.description]

# Convert fetched rows to DataFrame
df_IA = pd.DataFrame(rows, columns=columns)

# Close the cursor
cursor.close()

st.table(data=df_IA)



