import streamlit as st

def initialize_state():
    """
    Initialize all session state variables.
    """
    default_state = {
        "messages": [],
        "start_flg": False,
        "pre_mode": "",
        "shadowing_flg": False,
        "shadowing_button_flg": False,
        "shadowing_count": 0,
        "shadowing_first_flg": True,
        "shadowing_audio_input_flg": False,
        "shadowing_evaluation_first_flg": True,
        "dictation_flg": False,
        "dictation_button_flg": False,
        "dictation_count": 0,
        "dictation_first_flg": True,
        "dictation_chat_message": "",
        "dictation_evaluation_first_flg": True,
        "chat_open_flg": False,
        "problem": "",
        "paused": False
    }

    for key, value in default_state.items():
        if key not in st.session_state:
            st.session_state[key] = value

def reset_state():
    """
    Reset session state to its default values.
    """
    initialize_state()
    st.session_state["messages"] = []
    st.session_state["start_flg"] = False
    st.session_state["pre_mode"] = ""
    st.session_state["chat_open_flg"] = False