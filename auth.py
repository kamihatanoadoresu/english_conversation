import streamlit as st
import bcrypt
import json
import os
from pathlib import Path

# =========================
# ユーザー認証システム
# =========================

# ユーザーデータベースを外部ファイルから読み込み
# .pathファイルにbcryptでハッシュ化されたパスワードを保存
def load_users():
    """
    .pathファイルからユーザー情報を読み込む
    """
    path_file = Path(__file__).parent / ".path"
    if path_file.exists():
        with open(path_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    else:
        st.error("認証ファイルが見つかりません。")
        return {}

USERS = load_users()


def verify_credentials(username: str, password: str) -> bool:
    """
    ユーザー名とパスワードを検証（bcryptを使用）
    
    Args:
        username: ユーザー名
        password: パスワード
        
    Returns:
        認証が成功した場合はTrue、失敗した場合はFalse
    """
    if username in USERS:
        stored_hash = USERS[username].encode('utf-8')
        return bcrypt.checkpw(password.encode('utf-8'), stored_hash)
    return False


def login():
    """
    ログイン画面を表示し、認証処理を実行
    """
    # ページ中央にログインフォームを配置
    st.markdown("## 🔐 ログイン")
    st.markdown("アプリケーションを使用するにはログインしてください。")
    st.divider()
    
    # ログインフォーム
    with st.form("login_form"):
        username = st.text_input("ユーザー名", placeholder="ユーザー名を入力")
        password = st.text_input("パスワード", type="password", placeholder="パスワードを入力")
        submit = st.form_submit_button("ログイン", use_container_width=True, type="primary")
        
        if submit:
            if not username or not password:
                st.error("ユーザー名とパスワードを入力してください。")
            elif verify_credentials(username, password):
                st.session_state.authenticated = True
                st.session_state.username = username
                st.success(f"ようこそ、{username}さん！")
                st.rerun()
            else:
                st.error("ユーザー名またはパスワードが正しくありません。")


def logout():
    """
    ログアウト処理
    - セッションステートを完全にクリアして前のユーザーの情報を削除
    """
    # 認証情報をクリア
    st.session_state.authenticated = False
    st.session_state.username = None
    
    # セッション全体をクリアして会話履歴やLLMメモリも削除
    keys_to_keep = ['authenticated', 'username']
    for key in list(st.session_state.keys()):
        if key not in keys_to_keep:
            del st.session_state[key]
    
    st.rerun()


def check_authentication() -> bool:
    """
    認証状態を確認
    
    Returns:
        認証済みの場合はTrue、それ以外はFalse
    """
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    
    return st.session_state.authenticated
