import streamlit as st
import os
import time
from pathlib import Path
# import wave
# import pyaudio
from pydub import AudioSegment
from audiorecorder import audiorecorder
import numpy as np
from scipy.io.wavfile import write
from langchain.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    MessagesPlaceholder,
)
from langchain.schema import SystemMessage
from langchain.memory import ConversationSummaryBufferMemory
from langchain_openai import ChatOpenAI
from langchain.chains import ConversationChain
import constants as ct
import uuid  # 一意のファイル名生成のためにuuidをインポート

def record_audio(audio_input_file_path):
    """
    音声入力を受け取って音声ファイルを作成
    """

    audio = audiorecorder(
        start_prompt="発話開始",
        pause_prompt="やり直す",
        stop_prompt="発話終了",
        start_style={"color":"white", "background-color":"black"},
        pause_style={"color":"gray", "background-color":"white"},
        stop_style={"color":"white", "background-color":"black"}
    )

    if len(audio) > 0:
        audio.export(audio_input_file_path, format="wav")
    else:
        st.stop()

def transcribe_audio(audio_input_file_path):
    """
    音声入力ファイルから文字起こしテキストを取得
    Args:
        audio_input_file_path: 音声入力ファイルのパス
    Returns:
        transcript: Whisperの文字起こし結果
        warning_message: 警告メッセージ（なければNone）
    """

    # 音声ファイルの長さをチェック
    audio = AudioSegment.from_wav(audio_input_file_path)
    duration_seconds = len(audio) / 1000.0  # ミリ秒から秒に変換
    
    warning_message = None
    
    # 音声の長さをチェック
    if duration_seconds < 0.5:
        warning_message = "⚠️ 音声が非常に短いです。もう一度、発話してみてください。"

    with open(audio_input_file_path, 'rb') as audio_input_file:
        transcript = st.session_state.openai_obj.audio.transcriptions.create(
            model="whisper-1",
            file=audio_input_file,
            language="en"
        )
    
    # 文字起こし結果が空または非常に短い場合
    if not transcript.text or len(transcript.text.strip()) < 3:
        warning_message = "⚠️ 音声を認識できませんでした。もう一度、はっきりと発話してみてください。"
    
    # 音声入力ファイルを削除
    os.remove(audio_input_file_path)

    return transcript, warning_message

def save_to_wav(llm_response_audio, audio_output_file_path):
    """
    一旦mp3形式で音声ファイル作成後、wav形式に変換
    Args:
        llm_response_audio: LLMからの回答の音声データ
        audio_output_file_path: 出力先のファイルパス
    """

    temp_audio_output_filename = f"{ct.AUDIO_OUTPUT_DIR}/temp_audio_output_{int(time.time())}.mp3"
    with open(temp_audio_output_filename, "wb") as temp_audio_output_file:
        temp_audio_output_file.write(llm_response_audio)
    
    audio_mp3 = AudioSegment.from_file(temp_audio_output_filename, format="mp3")
    audio_mp3.export(audio_output_file_path, format="wav")

    # 音声出力用に一時的に作ったmp3ファイルを削除
    os.remove(temp_audio_output_filename)

# def play_wav(audio_output_file_path, speed=1.0):
#     """
#     音声ファイルの読み上げ
#     Args:
#         audio_output_file_path: 音声ファイルのパス
#         speed: 再生速度（1.0が通常速度、0.5で半分の速さ、2.0で倍速など）
#     """

#     # 音声ファイルの読み込み
#     audio = AudioSegment.from_wav(audio_output_file_path)
    
#     # 速度を変更
#     if speed != 1.0:
#         # frame_rateを変更することで速度を調整
#         modified_audio = audio._spawn(
#             audio.raw_data, 
#             overrides={"frame_rate": int(audio.frame_rate * speed)}
#         )
#         # 元のframe_rateに戻すことで正常再生させる（ピッチを保持したまま速度だけ変更）
#         modified_audio = modified_audio.set_frame_rate(audio.frame_rate)

#         modified_audio.export(audio_output_file_path, format="wav")

#     # PyAudioで再生
#     with wave.open(audio_output_file_path, 'rb') as play_target_file:
#         p = pyaudio.PyAudio()
#         stream = p.open(
#             format=p.get_format_from_width(play_target_file.getsampwidth()),
#             channels=play_target_file.getnchannels(),
#             rate=play_target_file.getframerate(),
#             output=True
#         )

#         data = play_target_file.readframes(1024)
#         while data:
#             stream.write(data)
#             data = play_target_file.readframes(1024)

#         stream.stop_stream()
#         stream.close()
#         p.terminate()
    
#     # LLMからの回答の音声ファイルを削除
#     os.remove(audio_output_file_path)

# ！上記関数の代替として、再生速度変更用関数を追加
def change_speed(input_wav, output_wav, speed):
    """
    音声ファイルの再生速度を変更して保存
    Args:
        input_wav: 入力WAVファイルのパス
        output_wav: 出力WAVファイルのパス
        speed: 再生速度（1.0が通常速度、0.5で半分の速さ、2.0で倍速など）
    """
    audio = AudioSegment.from_wav(input_wav)
    audio = audio.speedup(playback_speed=speed)
    audio.export(output_wav, format="wav")

def create_chain(system_template):
    """
    LLMによる回答生成用のChain作成
    """

    prompt = ChatPromptTemplate.from_messages([
        SystemMessage(content=system_template),
        MessagesPlaceholder(variable_name="history"),
        HumanMessagePromptTemplate.from_template("{input}")
    ])
    chain = ConversationChain(
        llm=st.session_state.llm,
        memory=st.session_state.memory,
        prompt=prompt
    )

    return chain

def create_problem_and_play_audio():
    """
    問題生成と音声ファイルの再生
    Args:
        chain: 問題文生成用のChain
        speed: 再生速度（1.0が通常速度、0.5で半分の速さ、2.0で倍速など）
        openai_obj: OpenAIのオブジェクト
    """

    # 問題文を生成するChainを実行し、問題文を取得
    problem = st.session_state.chain_create_problem.predict(input="")

    # LLMからの回答を音声データに変換
    llm_response_audio = st.session_state.openai_obj.audio.speech.create(
        model="tts-1",
        voice="alloy",
        input=problem
    )

    # 音声ファイルの作成
    audio_output_file_path = f"{ct.AUDIO_OUTPUT_DIR}/audio_output_{int(time.time())}.wav"
    save_to_wav(llm_response_audio.content, audio_output_file_path)

    # 音声ファイルの再生処理を変更
    # play_wav(audio_output_file_path, st.session_state.speed)  # 元のコードをコメントアウト
    if st.session_state.speed != 1.0:
        temp_audio_path = f"temp_{uuid.uuid4().hex}.wav"
        change_speed(audio_output_file_path, temp_audio_path, st.session_state.speed)
        audio_output_file_path = temp_audio_path

    return problem, llm_response_audio

def create_evaluation():
    """
    ユーザー入力値の評価生成
    """

    llm_response_evaluation = st.session_state.chain_evaluation.predict(input="")

    return llm_response_evaluation

def correct_user_input(user_text, level):
    """
    ユーザーの英語発話を添削し、より良い表現を提示
    Args:
        user_text: ユーザーの英語発話
        level: ユーザーの英語レベル
    Returns:
        correction: 添削結果（改善が必要ない場合はNone）
    """
    correction_prompt = f"""
You are an English grammar expert. Analyze the following English sentence and provide corrections if needed.

User's English Level: {level}
User's sentence: "{user_text}"

If the sentence has grammatical errors or could be improved:
1. Provide a corrected/improved version
2. Briefly explain the improvements in Japanese
3. Keep the original meaning intact

If the sentence is already correct and natural, simply respond with: "Perfect! No corrections needed."

Format your response as:
【改善案】
[Improved English sentence]

【解説】
[Brief explanation in Japanese]
"""
    
    correction = st.session_state.llm.predict(correction_prompt)
    
    # 添削が不要な場合はNoneを返す
    if "Perfect" in correction or "No corrections needed" in correction:
        return None
    
    return correction

def translate_to_japanese(english_text):
    """
    英語テキストを日本語に翻訳
    Args:
        english_text: 英語テキスト
    Returns:
        japanese_text: 日本語訳
    """
    translation_prompt = f"""
Translate the following English text to natural Japanese.
Provide only the Japanese translation without any additional explanation.

English: "{english_text}"

Japanese:
"""
    
    japanese_text = st.session_state.llm.predict(translation_prompt)
    
    return japanese_text.strip()

def correct_and_translate_batch(user_text, ai_response, level):
    """
    ユーザー発話の添削とAI返事の翻訳を1回のLLM呼び出しで取得（トークン節約）
    Args:
        user_text: ユーザーの英語発話
        ai_response: AIの英語返事
        level: ユーザーの英語レベル
    Returns:
        correction: 添削結果（改善不要の場合None）
        translation: 日本語訳
    """
    batch_prompt = f"""You must perform TWO tasks and return results in EXACT format below.

TASK 1 - Grammar Check
User's Level: {level}
User said: "{user_text}"

If there are errors or improvements needed:
- Provide corrected English sentence
- Explain improvements in Japanese
If already perfect, output only: PERFECT

TASK 2 - Translation
AI said: "{ai_response}"
Translate to natural Japanese.

CRITICAL: Use EXACTLY this format with markers:
<<<CORRECTION_START>>>
[Your correction result here - either "PERFECT" or corrected sentence with Japanese explanation]
<<<CORRECTION_END>>>

<<<TRANSLATION_START>>>
[Japanese translation here]
<<<TRANSLATION_END>>>
"""
    
    result = st.session_state.llm.predict(batch_prompt)
    
    # 結果を分割（改善されたパース処理）
    correction = None
    translation = ""
    
    try:
        # 添削部分を抽出
        if "<<<CORRECTION_START>>>" in result and "<<<CORRECTION_END>>>" in result:
            correction_start = result.find("<<<CORRECTION_START>>>") + len("<<<CORRECTION_START>>>")
            correction_end = result.find("<<<CORRECTION_END>>>")
            correction_part = result[correction_start:correction_end].strip()
            
            # "PERFECT"でなければ添削結果として保持
            if "PERFECT" not in correction_part.upper():
                correction = correction_part
        
        # 翻訳部分を抽出
        if "<<<TRANSLATION_START>>>" in result and "<<<TRANSLATION_END>>>" in result:
            translation_start = result.find("<<<TRANSLATION_START>>>") + len("<<<TRANSLATION_START>>>")
            translation_end = result.find("<<<TRANSLATION_END>>>")
            translation = result[translation_start:translation_end].strip()
    
    except Exception as e:
        # パース失敗時のフォールバック
        st.warning(f"⚠️ 添削・翻訳の解析に失敗しました: {e}")
        # 少なくとも何か返す
        if "PERFECT" not in result.upper():
            correction = result[:500]  # 最初の部分を返す
    
    return correction, translation