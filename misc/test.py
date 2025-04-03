## Data Pull ##
# Set default values
today = datetime.date.today()
yesterday = today - datetime.timedelta(days=1)
pull_range = yesterday - datetime.timedelta(days=60)
# Date range input with constraints
with st.form("Test"):
    start_date, end_date = st.date_input(
        "Select date range:",
        [yesterday-datetime.timedelta(days=1), yesterday],  # Default selection
        min_value=pull_range,     # Minimum selectable date
        max_value=yesterday           # Maximum selectable date
    )
    st.text("When selecting a single day:\nSelect the day you would like to look at, then select that day+1")
    run_pull = st.form_submit_button("Enter")
    if run_pull:
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
        SELECT DISTINCT record_user, log_comment
        FROM mpcs.mpcs_log
        WHERE log_date BETWEEN TO_DATE('{start_date_str}', 'DD-MON-YYYY') 
                        AND TO_DATE('{end_date_str}', 'DD-MON-YYYY')
        AND table_nm LIKE 'SHIP_RELEASE%'
        AND screen_nm LIKE 'RELEASE.SQR%'
        AND log_comment LIKE 'REL%PRINTED%(Acc%'
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
        ## Connection + Pull
        conn = cx_Oracle.connect(user=username, password=password, dsn=dsn_tns)
        # Table 1 - Override on Inspection A #
        # Create a cursor object
        cursor = conn.cursor()
        # Execute the query
        cursor.execute(query_IA)
        # Fetch all rows from the result
        rows = cursor.fetchall()
        # Get column names from cursor description
        columns = [col[0] for col in cursor.description]
        # Convert fetched rows to DataFrame
        df_IA = pd.DataFrame(rows, columns=columns)
        # Close the cursor
        cursor.close()
        # Table 2 - Override Inspection B #
        #Create a cursor object
        cursor = conn.cursor()
        # Execute the query
        cursor.execute(query_IB)
        # Fetch all rows from the result
        rows = cursor.fetchall()
        # Get column names from cursor description
        columns = [col[0] for col in cursor.description]
        # Convert fetched rows to DataFrame
        df_IB = pd.DataFrame(rows, columns=columns)
        # Close the cursor
        cursor.close()
        # Table 3 - Missing Manufacturing Feature #
        # Create a cursor object
        cursor = conn.cursor()
        # Execute the query
        cursor.execute(query_MMF)
        # Fetch all rows from the result
        rows = cursor.fetchall() 
        # Get column names from cursor description
        columns = [col[0] for col in cursor.description]
        # Convert fetched rows to DataFrame
        df_MMF = pd.DataFrame(rows, columns=columns)
        # Close the cursor
        cursor.close()
        # Connection close
        conn.close()

        ## Data Clean ##
        # df_IA
        cat_cols = ['PROCESS_PLAN_ID', 'INSPECT_TYPE', 'INSPECTION_ID', 'SERIAL_NO', 'INSP_EMP_ID', 'PART_PROGRAM']
        date_time_cols = ['DATE_TIME']	
        # date_format = "%Y-%m-%d %H:%M:%S"
        object_cols = ['ACCEPT_COMMENT']
        # Assigning
        df_IA[cat_cols] = df_IA[cat_cols].astype('category')
        df_IA[date_time_cols] = df_IA[date_time_cols].apply(pd.to_datetime, format="mixed")
        df_IA[object_cols] = df_IA[object_cols].astype('object')

        # df_IB
        # Splitting
        df_IB['RELEASE_NUMBER'] = df_IB['LOG_COMMENT'].str.extract(r'REL: (\d+)')
        df_IB['ACCEPTED'] = df_IB['LOG_COMMENT'].str.extract(r'Accepted: (\d+)').astype(int)
        df_IB['TOTAL'] = df_IB['LOG_COMMENT'].str.extract(r'Out of: (\d+)').astype(int)
        df_IB['PROGRAM'] = df_IB['LOG_COMMENT'].str.extract(r'sampling not enough for: (.*?);?\)')
        # Convert RELEASE_NUMBER to integer
        df_IB['RELEASE_NUMBER'] = df_IB['RELEASE_NUMBER'].astype(int)
        # Drop the original log column
        df_IB = df_IB.drop(columns=['LOG_COMMENT'])
        # Data type conversion
        cat_cols = ['RECORD_USER', 'RELEASE_NUMBER', 'PROGRAM']
        # Assigning
        df_IB[cat_cols] = df_IB[cat_cols].astype('category')

        # df_MMF
        # Splitting 'CURRENT_OPER_DESC' into 'OP' and 'OP_DESC'
        df_MMF['OP'] = df_MMF['CURRENT_OPER_DESC'].str.extract(r'^(\d+)')  # Extracts the leading number
        df_MMF['OP_DESC'] = df_MMF['CURRENT_OPER_DESC'].str.extract(r'^\d+\s*-\s*(.*)')  # Extracts the text after the dash
        # Splitting 'CURRENT_FEATURE_COUNT' into 'VANE', 'LOOP_CNT', 'REQD_FEATURES', and 'TOTAL'
        df_MMF[['VANE', 'LOOP_CNT', 'REQD_FEATURES', 'TOTAL']] = df_MMF['CURRENT_FEATURE_COUNT'].str.extract(
            r'VANE: (\d+) - LOOP CNT: (\d+) - REQRD FEATURES: (\d+) - TOTAL: (\d+)'
        )
        # Converting extracted numeric columns to integers
        df_MMF[['VANE', 'LOOP_CNT', 'REQD_FEATURES', 'TOTAL']] = df_MMF[['VANE', 'LOOP_CNT', 'REQD_FEATURES', 'TOTAL']].apply(pd.to_numeric)
        df_MMF.drop(columns = ['CURRENT_OPER_DESC', 'CURRENT_FEATURE_COUNT'], inplace=True)
        # Data Types
        cat_cols = ['PROCESS_PLAN_ID', 'PROCESS_STEP_ID', 'LOT_NO', 'SERIAL_NO','ACCEPT_EMP_ID', 'CURRENT_PART_PROGRAM', 'OP']
        date_time_cols = ['DATE_TIME']	
        object_cols = ['ACCEPT_COMMENTS', 'OP_DESC']
        # Assigning
        df_MMF[cat_cols] = df_MMF[cat_cols].astype('category')
        df_MMF[date_time_cols] = df_MMF[date_time_cols].apply(pd.to_datetime, format="mixed")
        df_MMF[object_cols] = df_MMF[object_cols].astype('object')


        ## Chart Area ##
        # Plan ID + OP - missing feature
         # Count occurrences of each (PROCESS_PLAN_ID, OP) pair
        df_count = df_MMF.groupby(['PROCESS_PLAN_ID', 'OP'], observed=True).size().reset_index(name='Count')

        # Sort by count in descending order and select the top 20
        df_top10 = df_count.sort_values(by='Count', ascending=False).head(20)

        # Create a formatted column for x-axis labels
        df_top10['PLAN_OP'] = df_top10['PROCESS_PLAN_ID'].astype(str) + " - OP " + df_top10['OP'].astype(str)

        # Ensure session state exists
        if "selected_plan_op" not in st.session_state:
            st.session_state.selected_plan_op = None

        # Create the bar chart using Plotly Graph Objects (go.Figure)
        fig = go.Figure()

        # Add bars to the figure
        fig.add_trace(go.Bar(
            x=df_top10['PLAN_OP'],
            y=df_top10['Count'],
            text=df_top10['Count'],
            textposition='outside',
            hoverinfo='x+y+text',
            marker=dict(color=df_top10['PROCESS_PLAN_ID'].map({
                'A': 'red', 'B': 'blue', 'C': 'green', 'D': 'purple', 'E': 'orange'
            }))
        ))

        # Update layout to include axis labels and title
        fig.update_layout(
            title="Top 10 Most Frequent PROCESS_PLAN_ID and OP Combinations",
            xaxis_title="PROCESS_PLAN_ID - OP",
            yaxis_title="Count",
            xaxis=dict(tickangle=-45),
            bargap=0.2,
            width=1000,
            height=500,
            colorway=["red", "blue", "green", "purple", "orange"]
        )

        # Display the plot
        st.plotly_chart(fig, use_container_width=True)

        # Create a dropdown to select the Plan ID and OP after chart interaction
        selected_plan_op = st.selectbox("Select a Process Plan ID and OP combination", df_top10['PLAN_OP'])

        # Filter the original dataframe based on the selection
        if selected_plan_op:
            try:
                selected_plan_id, selected_op = selected_plan_op.split(" - OP ")
                selected_op = int(selected_op)  # Convert OP to integer

                # Filter the original dataframe
                filtered_df = df_MMF[(df_MMF['PROCESS_PLAN_ID'] == selected_plan_id) & (df_MMF['OP'] == selected_op)]

                # Display filtered data
                st.write(f"### Entries for {selected_plan_id} - OP {selected_op}:")
                st.dataframe(filtered_df)

            except Exception as e:
                st.error(f"Error processing selection: {e}")