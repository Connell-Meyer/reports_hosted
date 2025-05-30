# data_utils.py
# This is a place for Data related functions to be called on in the main code
import pandas as pd
import os
import cx_Oracle
from dotenv import load_dotenv

# Load environment variables from .env file (for local development)
load_dotenv()

# Track whether the client has been initialized
oracle_client_initialized = False

def get_oracle_connection():
    global oracle_client_initialized

    user = os.getenv("DB_USER")
    password = os.getenv("DB_PASSWORD")
    host = os.getenv("DB_HOST")
    port = os.getenv("DB_PORT", "1521")
    service = os.getenv("DB_SERVICE")
    dsn = cx_Oracle.makedsn(host, port, service_name=service)

    # Only initialize once
    if not oracle_client_initialized:
        try:
            os.environ['LD_LIBRARY_PATH'] = "/opt/oracle/lib:" + os.environ.get('LD_LIBRARY_PATH', '')
            cx_Oracle.init_oracle_client(lib_dir="/opt/oracle/lib")  # Updated path for Linux
            oracle_client_initialized = True
        except cx_Oracle.ProgrammingError as e:
            # Raised if already initialized — safe to ignore
            pass
        except Exception as e:
            raise RuntimeError("Oracle Client initialization failed. Make sure Instant Client is installed.") from e

    return cx_Oracle.connect(user=user, password=password, dsn=dsn)


def build_queries(start_date_str, end_date_str):
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

    return query_IA, query_IB, query_MMF


def run_query(conn, query):
    with conn.cursor() as cursor:
        cursor.execute(query)
        rows = cursor.fetchall()
        columns = [col[0] for col in cursor.description]
        return pd.DataFrame(rows, columns=columns)


def clean_df_IA(df):
    cat_cols = ['PROCESS_PLAN_ID', 'INSPECT_TYPE', 'INSPECTION_ID', 'SERIAL_NO', 'INSP_EMP_ID', 'PART_PROGRAM']
    date_time_cols = ['DATE_TIME']
    object_cols = ['ACCEPT_COMMENT']
    df[cat_cols] = df[cat_cols].astype('category')
    df[date_time_cols] = df[date_time_cols].apply(pd.to_datetime, format="mixed")
    df[object_cols] = df[object_cols].astype('object')
    return df


def clean_df_IB(df):
    df['RELEASE_NUMBER'] = df['LOG_COMMENT'].str.extract(r'REL: (\d+)').astype(int)
    df['ACCEPTED'] = df['LOG_COMMENT'].str.extract(r'Accepted: (\d+)').astype(int)
    df['TOTAL'] = df['LOG_COMMENT'].str.extract(r'Out of: (\d+)').astype(int)
    df['PROGRAM'] = df['LOG_COMMENT'].str.extract(r'sampling not enough for: (.*?);?\)')
    df.drop(columns=['LOG_COMMENT'], inplace=True)
    cat_cols = ['RECORD_USER', 'RELEASE_NUMBER', 'PROGRAM']
    df[cat_cols] = df[cat_cols].astype('category')
    return df


def clean_df_MMF(df):
    df['OP'] = df['CURRENT_OPER_DESC'].str.extract(r'^(\d+)')
    df['OP_DESC'] = df['CURRENT_OPER_DESC'].str.extract(r'^\d+\s*-\s*(.*)')
    df[['VANE', 'LOOP_CNT', 'REQD_FEATURES', 'TOTAL']] = df['CURRENT_FEATURE_COUNT'].str.extract(
        r'VANE: (\d+) - LOOP CNT: (\d+) - REQRD FEATURES: (\d+) - TOTAL: (\d+)'
    )
    df[['VANE', 'LOOP_CNT', 'REQD_FEATURES', 'TOTAL']] = df[['VANE', 'LOOP_CNT', 'REQD_FEATURES', 'TOTAL']].apply(pd.to_numeric)
    df.drop(columns=['CURRENT_OPER_DESC', 'CURRENT_FEATURE_COUNT'], inplace=True)
    cat_cols = ['PROCESS_PLAN_ID', 'PROCESS_STEP_ID', 'LOT_NO', 'SERIAL_NO', 'ACCEPT_EMP_ID', 'CURRENT_PART_PROGRAM', 'OP']
    date_time_cols = ['DATE_TIME']
    object_cols = ['ACCEPT_COMMENTS', 'OP_DESC']
    df[cat_cols] = df[cat_cols].astype('category')
    df[date_time_cols] = df[date_time_cols].apply(pd.to_datetime, format="mixed")
    df[object_cols] = df[object_cols].astype('object')
    return df


def build_summary_queries(start_date_str, end_date_str, granularity):
    if granularity == "Daily":
        date_format = 'YYYY-MM-DD'
    elif granularity == "Weekly":
        date_format = 'IYYY-IW'  # ISO Year-Week
    elif granularity == "Monthly":
        date_format = 'YYYY-MM'
    else:
        raise ValueError("Invalid granularity. Choose 'Daily', 'Weekly', or 'Monthly'.")

    # --- IA ---
    query_IA_summary = f"""
    SELECT TO_CHAR(date_time, '{date_format}') AS EVENT_DATE, COUNT(*) AS COUNT
    FROM inspect.inspect_sum_results
    WHERE date_time BETWEEN TO_DATE('{start_date_str}', 'DD-MON-YYYY') 
                        AND TO_DATE('{end_date_str}', 'DD-MON-YYYY')
      AND insp_mach_id IN (
          SELECT machine_id FROM mpcs.machine WHERE NVL(machine_type, 'x') = 'DEPARTMENT'
      )
    GROUP BY TO_CHAR(date_time, '{date_format}')
    ORDER BY EVENT_DATE
    """

    # --- IB ---
    query_IB_summary = f"""
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
    SELECT TO_CHAR(l.log_date, '{date_format}') AS EVENT_DATE, COUNT(DISTINCT r.release_no) AS COUNT
    FROM mpcs.mpcs_log l
    JOIN ranked_ships r ON r.release_no = REGEXP_SUBSTR(l.log_comment, 'REL: ([0-9]+)', 1, 1, NULL, 1)
    JOIN mpcs.lot lot ON r.lot_no = lot.lot_no
    JOIN mpcs.part_resource res ON r.resource_no = res.resource_no AND r.resource_type = res.resource_type
    WHERE l.log_date BETWEEN TO_DATE('{start_date_str}', 'DD-MON-YYYY') 
                          AND TO_DATE('{end_date_str}', 'DD-MON-YYYY')
      AND l.table_nm LIKE 'SHIP_RELEASE%'
      AND l.screen_nm LIKE 'RELEASE.SQR%'
      AND l.log_comment LIKE 'REL%PRINTED%(Acc%)'
      AND r.rn = 1
    GROUP BY TO_CHAR(l.log_date, '{date_format}')
    ORDER BY EVENT_DATE
    """

    # --- MMF ---
    query_MMF_summary = f"""
    SELECT TO_CHAR(date_time, '{date_format}') AS EVENT_DATE, COUNT(*) AS COUNT
    FROM mpcs.mfg_process_accept
    WHERE date_time BETWEEN TO_DATE('{start_date_str}', 'DD-MON-YYYY') 
                        AND TO_DATE('{end_date_str}', 'DD-MON-YYYY')
    GROUP BY TO_CHAR(date_time, '{date_format}')
    ORDER BY EVENT_DATE
    """

    return query_IA_summary, query_IB_summary, query_MMF_summary
