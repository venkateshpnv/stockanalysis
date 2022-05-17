import streamlit as st
from DB import *


if __name__ == "__main__":
    st.write(f"""
    # Settings values

    - **Input**: {st.session_state.text}
    - **Slider**: `{st.session_state.slider}`
    - **Checkbox**: `{st.session_state.checkbox}`
    - **Radio**: {st.session_state.radio}
    - **Selectbox**: {st.session_state.selectbox}
    - **Multiselect**: {", ".join(st.session_state.multiselect)}
    """)


