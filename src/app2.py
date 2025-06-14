import streamlit as st

st.set_page_config(page_title="Ask Impact Theory", 
                   page_icon="data/logos/great_logos.png", 
                   layout="wide", 
                   initial_sidebar_state="collapsed", 
                   menu_items={'Report a bug': "https://www.extremelycoolapp.com/bug"})

st.title("Chat with our crypto agents on Discord!")

st.image('data/logos/great_logo.png', use_column_width=True)
