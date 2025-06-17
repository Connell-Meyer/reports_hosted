### Initialization Improts ###
import streamlit as st
import pandas as pd

df = pd.read_csv(r"\\mti\fileshares\HQ DCI\Connell Phillipps\test_data.csv")

### Page Setup ###
st.set_page_config(
    layout="centered",
    initial_sidebar_state="expanded",
    page_title='Cost of Poor Quality',
    page_icon='💰'
)
st.logo('./misc/meyer-logo.png')


### Page Start ###
st.title("Cost of Poor Quality")
st.markdown("WORK IN PROGRESS")

st.markdown("Test")
st.dataframe(df)

