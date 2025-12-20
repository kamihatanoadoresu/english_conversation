import os
import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI
from langchain.memory import ConversationSummaryBufferMemory
from langchain_openai import ChatOpenAI

import constants as ct
import functions as ft
from state_manager import initialize_state
import auth


def initialize():
    """
    アプリ起動時の初期化処理
    - 認証チェック
    - session_state 初期化
    - 外部リソース生成
    - サイドバーUI
    """
    # =========================
    # 認証チェック
    # =========================
    if not auth.check_authentication():
        auth.login()
        st.stop()
    
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

        # 日常英会話モードの添削・翻訳機能
        st.divider()
        st.markdown("**日常英会話モード追加機能**")
        st.session_state.show_corrections = st.checkbox(
            "📝 発話添削表示",
            value=st.session_state.get("show_corrections", True),
            help="あなたの英語を添削します（追加トークン消費）"
        )
        st.session_state.show_translation = st.checkbox(
            "🇯🇵 日本語訳表示",
            value=st.session_state.get("show_translation", True),
            help="AIの返事を日本語で表示（追加トークン消費）"
        )

        # 英語レベルが設定されたらchainを初期化
        if "chain_basic_conversation" not in st.session_state or st.session_state.get("prev_englv") != st.session_state.englv:
            st.session_state.chain_basic_conversation = ft.create_chain(
                ct.SYSTEM_TEMPLATE_BASIC_CONVERSATION.format(level=st.session_state.englv)
            )
            st.session_state.prev_englv = st.session_state.englv

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

        # ログアウトボタン（認証済みの場合のみ表示）
        st.divider()
        st.markdown(f"**ログイン中:** {st.session_state.username}")
        if st.button("ログアウト", use_container_width=True, key="logout_button"):
            auth.logout()

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
