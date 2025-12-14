import streamlit as st
from langchain.memory import ConversationSummaryBufferMemory
from langchain_openai import ChatOpenAI

# =========================
# セッションステート定義
# =========================

DEFAULT_STATE = {
    # 共通
    "messages": [],
    "start_flg": False,
    "mode": None,
    "pre_mode": None,

    # シャドーイング
    "shadowing_flg": False,
    "shadowing_button_flg": False,
    "shadowing_count": 0,
    "shadowing_first_flg": True,
    "shadowing_audio_input_flg": False,
    "shadowing_evaluation_first_flg": True,

    # ディクテーション
    "dictation_flg": False,
    "dictation_button_flg": False,
    "dictation_count": 0,
    "dictation_first_flg": True,
    "dictation_chat_message": "",
    "dictation_evaluation_first_flg": True,

    # その他
    "chat_open_flg": False,
    "problem": "",
}


# -------------------------
# 初回起動用
# -------------------------
def initialize_state():
    """
    初回起動時のみ session_state を初期化する
    """
    for key, value in DEFAULT_STATE.items():
        if key not in st.session_state:
            st.session_state[key] = value


# -------------------------
# 会話リセット
# -------------------------
def reset_conversation():
    """
    会話のみをリセットする
    - チャット履歴
    - LangChain memory
    """
    st.session_state.messages = []

    # 過去会話の要約・内部キャッシュ混入を防ぐため、ConversationMemoryを新規生成してLLM文脈を完全に初期化
    if "llm" in st.session_state:
        from langchain.memory import ConversationSummaryBufferMemory
        st.session_state.memory = ConversationSummaryBufferMemory(
            llm=st.session_state.llm,
            max_token_limit=1000,
            return_messages=True
        )

# -------------------------
# 完全リセット
# -------------------------
# def reset_state():
#     """
#     アプリ状態を完全に初期化する（通常は使わない）
#     """
#     st.session_state.clear()
#     initialize_state()
