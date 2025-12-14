import os
import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI
from langchain.memory import ConversationSummaryBufferMemory
from langchain_openai import ChatOpenAI

import constants as ct
import functions as ft
from state_manager import initialize_state


def initialize():
    """
    アプリ起動時の初期化処理
    - session_state 初期化
    - 外部リソース生成
    - サイドバーUI
    """
    # =========================
    # セッションステート初期化
    # =========================
    initialize_state()

    # =========================
    # 外部リソース初期化
    # =========================
    if "openai_obj" not in st.session_state:
        st.session_state.openai_obj = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

    if "llm" not in st.session_state:
        st.session_state.llm = ChatOpenAI(
            model_name="gpt-4o-mini",
            temperature=0.5
        )

    if "memory" not in st.session_state:
        st.session_state.memory = ConversationSummaryBufferMemory(
            llm=st.session_state.llm,
            max_token_limit=1000,
            return_messages=True
        )

    if "chain_basic_conversation" not in st.session_state:
        st.session_state.chain_basic_conversation = ft.create_chain(
            ct.SYSTEM_TEMPLATE_BASIC_CONVERSATION
        )

    # =========================
    # サイドバー UI
    # =========================
    with st.sidebar:
        st.markdown("**【操作説明】**")
        st.success("""
        - モードと再生速度を選択し、「開始」ボタンを押して英会話を始めましょう。
        - モードは「日常英会話」「シャドーイング」「ディクテーション」から選べます。
        - 「中断」ボタンを押すことで、英会話をリセットできます。
        """)
        st.divider()

        st.header("設定")
        st.session_state.mode = st.selectbox(
            "モード",
            [ct.MODE_1, ct.MODE_2, ct.MODE_3]
        )
        st.session_state.englv = st.selectbox(
            "英語レベル",
            ct.ENGLISH_LEVEL_OPTION
        )
        st.session_state.speed = st.selectbox(
            "再生速度",
            ct.PLAY_SPEED_OPTION,
            index=3
        )

        # =========================
        # モード変更時の制御
        # =========================
        if st.session_state.mode != st.session_state.pre_mode:
            st.session_state.start_flg = False
            st.session_state.chat_open_flg = False

            st.session_state.shadowing_count = 0
            st.session_state.dictation_count = 0

            if st.session_state.mode == ct.MODE_1:
                st.session_state.shadowing_flg = False
                st.session_state.dictation_flg = False

            elif st.session_state.mode == ct.MODE_2:
                st.session_state.dictation_flg = False

            elif st.session_state.mode == ct.MODE_3:
                st.session_state.shadowing_flg = False

        st.session_state.pre_mode = st.session_state.mode

    # =========================
    # 初回メッセージ
    # =========================
    if not st.session_state.messages:
        with st.chat_message("assistant", avatar="images/ai_icon.jpg"):
            st.markdown(
                "こちらは生成AIによる音声英会話の練習アプリです。"
                "何度も繰り返し練習し、英語力をアップさせましょう。"
            )


# 環境変数ロード
load_dotenv()
