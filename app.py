### Libraries ###
import streamlit as st
import st_pages
import pandas as pd
import numpy as np
import plotly.express as px

### Layout ###
st.set_page_config(
    layout="centered",
    initial_sidebar_state="expanded",
)
st.logo('./misc/meyer-logo.png')


### Page Start ###
# Logo
col1, col2, col3 = st.columns(3)
with col2:
    st.image('./misc/meyer-logo.png', use_container_width="auto")

# Title
st.title("Quality Reports")
st.divider()

st.title('test')
