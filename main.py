import streamlit as st
import os
import time
from time import sleep
from pathlib import Path
from streamlit.components.v1 import html
from langchain.memory import ConversationSummaryBufferMemory
from langchain.chains import ConversationChain
from langchain.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    MessagesPlaceholder,
)
from langchain.schema import SystemMessage
from openai import OpenAI
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
import functions as ft
import constants as ct
import uuid
from initialize import initialize
from state_manager import reset_conversation


# 各種設定
load_dotenv()
st.set_page_config(
    page_title=ct.APP_NAME
)

# タイトル表示
st.markdown(f"## {ct.APP_NAME}")

# 初期化処理
initialize()


# メッセージリストの一覧表示
if st.session_state.start_flg:
    for message in st.session_state.messages:
        if message["role"] == "assistant":
            with st.chat_message(message["role"], avatar="images/ai_icon.jpg"):
                st.markdown(message["content"])
        elif message["role"] == "user":
            with st.chat_message(message["role"], avatar="images/user_icon.jpg"):
                st.markdown(message["content"])
        else:
            st.divider()

# 会話開始ボタンと中断ボタンの切り替え
if st.session_state.start_flg:
    if st.button("中断", use_container_width=True):
        reset_conversation()
        st.session_state.start_flg = False
        st.rerun()
else:
    if st.button("開始", use_container_width=True, type="primary"):
        reset_conversation()
        st.session_state.start_flg = True
        st.session_state.show_reset_message = False
        st.rerun()

# 会話未開始の場合は以降の処理を停止
if not st.session_state.start_flg:
    st.stop()

# LLMレスポンスの下部にモード実行のボタン表示
if st.session_state.start_flg:
    if st.session_state.shadowing_flg:
        st.session_state.shadowing_button_flg = st.button("シャドーイング開始")
    if st.session_state.dictation_flg:
        st.session_state.dictation_button_flg = st.button("ディクテーション開始")

# 「ディクテーション」モードのチャット入力受付時に実行
if st.session_state.chat_open_flg:
    st.info("AIが読み上げた音声を、画面下部のチャット欄からそのまま入力・送信してください。")

# ディクテーションモード時のみチャット入力を表示
if st.session_state.mode == ct.MODE_3:
    st.session_state.dictation_chat_message = st.chat_input("AIの音声を聞いて、英文を入力してください")
else:
    st.session_state.dictation_chat_message = ""

if st.session_state.dictation_chat_message and not st.session_state.chat_open_flg:
    st.stop()

# 「英会話開始」ボタンが押された場合の処理
if st.session_state.start_flg:    
    # モード：「日常英会話」
    if st.session_state.mode == ct.MODE_1:
        # 音声入力を受け取って音声ファイルを作成
        audio_input_file_path = f"{ct.AUDIO_INPUT_DIR}/audio_input_{int(time.time())}.wav"
        try:
            ft.record_audio(audio_input_file_path)
        except Exception as e:
            st.error(f"音声の録音中にエラーが発生しました: {e}")
            st.stop()

        # 音声入力ファイルから文字起こしテキストを取得（自動判定→日本語なら英訳＋カタカナ発音）
        with st.spinner('音声入力をテキストに変換中...'):
            result = ft.transcribe_and_handle_language(audio_input_file_path)
            warning_message = result.get('warning_message')
            detected = result.get('detected_language')
            user_message_displayed = False

            # 日本語と判定された場合は日本語原文と英訳、カタカナ発音を表示し、英訳文で会話を続行
            if detected and str(detected).lower().startswith('ja') and result.get('translated_english'):
                japanese = result.get('original_text','')
                translated_en = result.get('translated_english','')
                katakana = result.get('katakana_pron','')

                with st.chat_message("user", avatar=ct.USER_ICON_PATH):
                    st.markdown(f"**(認識言語: 日本語)**\n{japanese}\n\n**英訳:**\n{translated_en}\n\n{katakana}")
                audio_input_text = translated_en
                user_message_displayed = True
            else:
                # 英語として扱う
                audio_input_text = result.get('original_text','')

            # 警告メッセージがあれば表示
            if warning_message:
                st.warning(warning_message)

        # 音声入力テキストの画面表示（日本語表示済みならスキップ）
        if not user_message_displayed:
            if not audio_input_text or len(str(audio_input_text).strip()) == 0:
                st.warning("⚠️ 音声を認識できませんでした。もう一度、はっきりと発話してみてください。")
                st.stop()
            with st.chat_message("user", avatar=ct.USER_ICON_PATH):
                st.markdown(audio_input_text)
        
        with st.spinner("回答の音声読み上げ準備中..."):
            # ユーザー入力値をLLMに渡して回答取得
            llm_response = st.session_state.chain_basic_conversation.predict(input=audio_input_text)
            
            # LLMからの回答を音声データに変換
            llm_response_audio = st.session_state.openai_obj.audio.speech.create(
                model="tts-1",
                voice="alloy",
                input=llm_response
            )

            # 一旦mp3形式で音声ファイル作成後、wav形式に変換
            audio_output_file_path = f"{ct.AUDIO_OUTPUT_DIR}/audio_output_{int(time.time())}.wav"
            ft.save_to_wav(llm_response_audio.content, audio_output_file_path)

        # 音声ファイルの読み上げ
        # ft.play_wav(audio_output_file_path, speed=st.session_state.speed)
        # play_wav 関数は変更されたため、以下のコードをコメントアウト
        # ft.play_wav(audio_output_file_path, speed=st.session_state.speed)

        # 代わりに change_speed を使用
        if st.session_state.speed != 1.0:
            temp_audio_path = f"{ct.AUDIO_OUTPUT_DIR}/temp_{uuid.uuid4().hex}.wav"
            ft.change_speed(audio_output_file_path, temp_audio_path, st.session_state.speed)
        else:
            temp_audio_path = audio_output_file_path

        st.session_state.temp_audio_path = temp_audio_path
        st.audio(temp_audio_path)

        # AIメッセージの画面表示とリストへの追加
        with st.chat_message("assistant", avatar=ct.AI_ICON_PATH):
            st.markdown(llm_response)
            
            # ユーザー発話の添削（ON時のみ）
            if st.session_state.show_corrections:
                with st.spinner('添削中...'):
                    correction = ft.correct_user_input(audio_input_text, st.session_state.englv)
                
                if correction:
                    with st.expander("📝 あなたの発話をより良くするには"):
                        st.markdown(correction)
            
            # AI返事の日本語訳（ON時のみ）
            if st.session_state.show_translation:
                with st.spinner('翻訳中...'):
                    translation = ft.translate_to_japanese(llm_response)
                
                if translation:
                    with st.expander("🇯🇵 日本語訳を見る"):
                        st.markdown(translation)

        # ユーザー入力値とLLMからの回答をメッセージ一覧に追加
        st.session_state.messages.append({"role": "user", "content": audio_input_text})
        st.session_state.messages.append({"role": "assistant", "content": llm_response})

    # モード：「シャドーイング」
    # 「シャドーイング」ボタン押下時か、「英会話開始」ボタン押下時
    if st.session_state.mode == ct.MODE_2 and (st.session_state.shadowing_button_flg or st.session_state.shadowing_count == 0 or st.session_state.shadowing_audio_input_flg):
        if st.session_state.shadowing_first_flg:
            system_template_with_level = ct.SYSTEM_TEMPLATE_CREATE_PROBLEM.format(level=st.session_state.englv)
            st.session_state.chain_create_problem = ft.create_chain(system_template_with_level)
            st.session_state.shadowing_first_flg = False
        
        if not st.session_state.shadowing_audio_input_flg:
            with st.spinner('問題文（教材）読み込み中...'):
                try:
                    block = ft.pick_shadowing_block_from_documents(ct.DOCUMENTS_DIR)
                    if not block:
                        # フォールバック: 既存の生成ロジックを使う
                        st.session_state.problem, llm_response_audio, audio_file_path = ft.create_problem_and_play_audio()
                    else:
                        # block contains english, japanese, katakana, grammar_unit
                        english = block.get('english','')
                        japanese = block.get('japanese','')
                        katakana = block.get('katakana','')
                        grammar_unit = block.get('grammar_unit','')

                        # 文法解説（LLMを最小活用）
                        grammar_explanation = ft.explain_grammar_for_shadowing(english, grammar_unit)

                        # 表示用に st.session_state.problem を英語文としてセット
                        st.session_state.problem = english

                        # 音声（TTS）を作成
                        try:
                            llm_response_audio = st.session_state.openai_obj.audio.speech.create(
                                model="tts-1",
                                voice="alloy",
                                input=english
                            )
                            audio_file_path = f"{ct.AUDIO_OUTPUT_DIR}/audio_output_{int(time.time())}.wav"
                            ft.save_to_wav(llm_response_audio.content, audio_file_path)
                        except Exception:
                            audio_file_path = None

                        # 問題文（教材）を表示（整形）
                        with st.chat_message("assistant", avatar=ct.AI_ICON_PATH):
                            md = f"**教材:** {block.get('_source_file','')} (index {block.get('_block_index')})\n\n"
                            md += f"**英文:**\n{english}\n\n"
                            if japanese:
                                md += f"**和訳:**\n{japanese}\n\n"
                            if katakana:
                                md += f"**発音:**\n{katakana}\n\n"
                            if grammar_unit:
                                md += f"**文法項目:**\n{grammar_unit}\n\n"
                            if grammar_explanation:
                                md += f"**文法解説:**\n{grammar_explanation}\n\n"
                            st.markdown(md)

                except Exception as e:
                    st.error(f"問題文（教材）読み込み中にエラーが発生しました: {e}")
                    st.stop()

        # 音声入力を受け取って音声ファイルを作成
        st.session_state.shadowing_audio_input_flg = True
        audio_input_file_path = f"{ct.AUDIO_INPUT_DIR}/audio_input_{int(time.time())}.wav"
        try:
            ft.record_audio(audio_input_file_path)
        except Exception as e:
            st.error(f"音声の録音中にエラーが発生しました: {e}")
            st.stop()
            
        st.session_state.shadowing_audio_input_flg = False

        with st.spinner('音声入力をテキストに変換中...'):
            # 音声入力ファイルから文字起こしテキストを取得
            transcript, warning_message = ft.transcribe_audio(audio_input_file_path)
            audio_input_text = transcript.text
            
            # 警告メッセージがあれば表示
            if warning_message:
                st.warning(warning_message)

        # AIメッセージとユーザーメッセージの画面表示
        with st.chat_message("assistant", avatar=ct.AI_ICON_PATH):
            st.markdown(st.session_state.problem)
        with st.chat_message("user", avatar=ct.USER_ICON_PATH):
            st.markdown(audio_input_text)
        
        # LLMが生成した問題文と音声入力値をメッセージリストに追加
        st.session_state.messages.append({"role": "assistant", "content": st.session_state.problem})
        st.session_state.messages.append({"role": "user", "content": audio_input_text})

        with st.spinner('評価結果の生成中...'):
            # 毎回現在の問題文と回答に基づいて評価プロンプトを直接LLMに投げる
            system_template = ct.SYSTEM_TEMPLATE_EVALUATION.format(
                llm_text=st.session_state.problem,
                user_text=audio_input_text,
                level=st.session_state.englv
            )
            try:
                llm_response_evaluation = st.session_state.llm.predict(system_template)
            except Exception as e:
                llm_response_evaluation = f"評価の生成に失敗しました: {e}"
        
        # 評価結果のメッセージリストへの追加と表示
        with st.chat_message("assistant", avatar=ct.AI_ICON_PATH):
            st.markdown(llm_response_evaluation)
        st.session_state.messages.append({"role": "assistant", "content": llm_response_evaluation})
        st.session_state.messages.append({"role": "other"})
        
        # 各種フラグの更新
        st.session_state.shadowing_flg = True
        st.session_state.shadowing_count += 1

        # 「シャドーイング」ボタンを表示するために再描画
        st.rerun()
    
    
    # モード：「ディクテーション」
    # 「ディクテーション」ボタン押下時か、「英会話開始」ボタン押下時か、チャット送信時
    if st.session_state.mode == ct.MODE_3 and (st.session_state.dictation_button_flg or st.session_state.dictation_count == 0 or st.session_state.dictation_chat_message):
        if st.session_state.dictation_first_flg:
            system_template_with_level = ct.SYSTEM_TEMPLATE_CREATE_PROBLEM.format(level=st.session_state.englv)
            st.session_state.chain_create_problem = ft.create_chain(system_template_with_level)
            st.session_state.dictation_first_flg = False
        # チャット入力以外
        if not st.session_state.chat_open_flg:
            with st.spinner('問題文生成中...'):
                try:
                    st.session_state.problem, llm_response_audio, audio_file_path = ft.create_problem_and_play_audio()
                    if not st.session_state.problem:
                        st.error("問題文の生成に失敗しました。もう一度お試しください。")
                        st.stop()
                    # 音声ファイルの表示（再生ボタン付き） - create_problem_and_play_audio が作成したファイルを使用
                    st.audio(audio_file_path)

                    # ディクテーション回答待ちのメッセージを表示
                    st.info("AIが読み上げた音声を、画面下部のチャット欄からそのまま入力・送信してください。")
                    st.session_state.chat_open_flg = True

                except Exception as e:
                    st.error(f"問題文生成中にエラーが発生しました: {e}")
                    st.stop()

        # チャット入力時の処理
        else:
            # チャット欄から入力された場合にのみ評価処理が実行されるようにする
            if not st.session_state.dictation_chat_message:
                st.stop()
            
            # AIメッセージとユーザーメッセージの画面表示
            with st.chat_message("assistant", avatar=ct.AI_ICON_PATH):
                st.markdown(st.session_state.problem)
            with st.chat_message("user", avatar=ct.USER_ICON_PATH):
                st.markdown(st.session_state.dictation_chat_message)

            # LLMが生成した問題文とチャット入力値をメッセージリストに追加
            st.session_state.messages.append({"role": "assistant", "content": st.session_state.problem})
            st.session_state.messages.append({"role": "user", "content": st.session_state.dictation_chat_message})
            
            with st.spinner('評価結果の生成中...'):
                system_template = ct.SYSTEM_TEMPLATE_EVALUATION.format(
                    llm_text=st.session_state.problem,
                    user_text=st.session_state.dictation_chat_message,
                    level=st.session_state.englv
                )
                st.session_state.chain_evaluation = ft.create_chain(system_template)
                # 問題文と回答を比較し、評価結果の生成を指示するプロンプトを作成
                llm_response_evaluation = ft.create_evaluation()
            
            # 評価結果のメッセージリストへの追加と表示
            with st.chat_message("assistant", avatar=ct.AI_ICON_PATH):
                st.markdown(llm_response_evaluation)
            st.session_state.messages.append({"role": "assistant", "content": llm_response_evaluation})
            st.session_state.messages.append({"role": "other"})
            
            # 各種フラグの更新
            st.session_state.dictation_flg = True
            st.session_state.dictation_chat_message = ""
            st.session_state.dictation_count += 1
            st.session_state.chat_open_flg = False

            st.rerun()