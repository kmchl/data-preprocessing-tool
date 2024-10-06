# app.py

import streamlit as st
from src.preprocessing.data_preprocessor import DataPreprocessor

st.title("Data Preprocessing Tool for Clinic Names and Isolated Organisms")

# Instantiate and run the app
if __name__ == "__main__":
    app = DataPreprocessor()
    app.run()