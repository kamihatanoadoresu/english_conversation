import os
from dotenv import load_dotenv
from openai import OpenAI
from langchain.memory import ConversationSummaryBufferMemory
from langchain_openai import ChatOpenAI
import constants as ct
import streamlit as st
import functions as ft
from state_manager import initialize_state

def initialize():
    """
    セッションステートの初期化処理とUIの初期表示を設定
    """
    # セッションステートの初期化
    initialize_state()

    st.session_state.openai_obj = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    st.session_state.llm = ChatOpenAI(model_name="gpt-4o-mini", temperature=0.5)
    st.session_state.memory = ConversationSummaryBufferMemory(
        llm=st.session_state.llm,
        max_token_limit=1000,
        return_messages=True
    )

    # モード「日常英会話」用のChain作成
    st.session_state.chain_basic_conversation = ft.create_chain(ct.SYSTEM_TEMPLATE_BASIC_CONVERSATION)

    # サイドバーでのUI初期表示
    with st.sidebar:
        st.markdown("**【操作説明】**")
        st.success("""
        - モードと再生速度を選択し、「開始」ボタンを押して英会話を始めましょう。
        - モードは「日常英会話」「シャドーイング」「ディクテーション」から選べます。
        - 「中断」ボタンを押すことで、英会話をリセットできます。
        """)
        st.divider()

        st.header("設定")
        st.session_state.mode = st.selectbox(label="モード", options=[ct.MODE_1, ct.MODE_2, ct.MODE_3])
        st.session_state.englv = st.selectbox(label="英語レベル", options=ct.ENGLISH_LEVEL_OPTION)
        st.session_state.speed = st.selectbox(label="再生速度", options=ct.PLAY_SPEED_OPTION, index=3)

        # モードを変更した際の処理
        if st.session_state.mode != st.session_state.pre_mode:
            st.session_state.start_flg = False
            if st.session_state.mode == ct.MODE_1:
                st.session_state.dictation_flg = False
                st.session_state.shadowing_flg = False
            st.session_state.shadowing_count = 0
            if st.session_state.mode == ct.MODE_2:
                st.session_state.dictation_flg = False
            st.session_state.dictation_count = 0
            if st.session_state.mode == ct.MODE_3:
                st.session_state.shadowing_flg = False
            st.session_state.chat_open_flg = False
        st.session_state.pre_mode = st.session_state.mode

    # 初回表示用メッセージ
    with st.chat_message("assistant", avatar="images/ai_icon.jpg"):
        st.markdown("こちらは生成AIによる音声英会話の練習アプリです。何度も繰り返し練習し、英語力をアップさせましょう。")

        
# 環境変数のロード
load_dotenv()