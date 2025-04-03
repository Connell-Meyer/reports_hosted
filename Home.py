### Libraries ###
import streamlit as st

### Page Setup ###
st.set_page_config(
    layout="centered",
    initial_sidebar_state="expanded",
    page_title="Home",
    page_icon='🏭'
)
st.logo('./misc/meyer-logo.png')


### Page Start ###
# Logo
col1, col2, col3 = st.columns(3)
with col2:
    st.image('./misc/meyer-logo.png', use_container_width=True)

# Title
st.title("Quality Reports")
st.divider()

# Trends
st.subheader("Override Report Trends")
st.text("Show trend of override numbers over the last couple of months/weeks")
