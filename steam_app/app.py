import pandas as pd
import requests
import streamlit as st

# --------------------------------------------------
# 1. ページ基本設定
# --------------------------------------------------
st.set_page_config(
    page_title="Steam プレイ時間取得ツール",
    page_icon="🎮",
    layout="centered",
)

# --------------------------------------------------
# 2. パスワード認証処理
# --------------------------------------------------
# クラウド側の Secrets からパスワードを取得（ローカルテスト時のデフォルト値: "pass123"）
try:
    APP_PASSWORD = st.secrets.get("APP_PASSWORD", "pass123")
except Exception:
    APP_PASSWORD = "pass123"

# セッション状態（ログインフラグ）の初期化
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

# 未ログイン時の画面表示
if not st.session_state.authenticated:
    st.title("🔒 ログインが必要です")
    user_input_pass = st.text_input(
        "合言葉（パスワード）を入力してください", type="password"
    )

    if st.button("ログイン", type="primary"):
        if user_input_pass == APP_PASSWORD:
            st.session_state.authenticated = True
            st.rerun()  # 画面をリロードして認証後画面へ遷移
        else:
            st.error("パスワードが違います。")

    # 認証が通るまではここで処理を打ち切る（メイン画面を実行させない）
    st.stop()

# --------------------------------------------------
# 3. メイン画面（認証成功時のみ実行）
# --------------------------------------------------
st.title("🎮 Steam プレイ時間取得ツール")
st.write(
    "Steam ID を入力して「データを取得」を押すと、所有ゲーム一覧とプレイ時間を取得してCSVで出力できます。"
)

# クラウド側の Secrets から API Key を取得（ローカルテスト時はサイドバーからも入力可能に）
try:
    api_key = st.secrets.get("STEAM_API_KEY", "")
except Exception:
    api_key = ""
if not api_key:
    api_key = st.sidebar.text_input(
        "Steam API Key (ローカルテスト用)", type="password"
    )

# ユーザー入力欄
steam_id = st.text_input(
    "Steam ID (17桁の数字)", placeholder="例: 76561198000000000"
)
st.caption(
    "※Steamの「プライバシー設定」で「ゲームの詳細」が「公開」になっている必要があります。"
)

if st.button("データを取得する", type="primary"):
    if not api_key:
        st.error(
            "APIキーが設定されていません。サイドバーに入力するか、Secretsに設定してください。"
        )
    elif not steam_id:
        st.warning("Steam ID を入力してください。")
    else:
        with st.spinner("Steamからデータを取得中..."):
            url = (
                "http://api.steampowered.com/IPlayerService/GetOwnedGames/v0001/"
            )
            params = {
                "key": api_key,
                "steamid": steam_id,
                "format": "json",
                "include_appinfo": True,
                "include_played_free_games": True,
            }

            response = requests.get(url, params=params)

            if response.status_code == 200:
                data = response.json()
                games = data.get("response", {}).get("games", [])

                if not games:
                    st.error(
                        "ゲームデータが見つかりませんでした。「ゲームの詳細」が「公開」になっているか確認してください。"
                    )
                else:
                    game_list = []
                    for g in games:
                        p_min = g.get("playtime_forever", 0)
                        p_2w_min = g.get("playtime_2weeks", 0)
                        game_list.append(
                            {
                                "ゲーム名": g.get("name", "不明"),
                                "App ID": g.get("appid"),
                                "総プレイ時間 (時間)": round(p_min / 60, 1),
                                "総プレイ時間 (分)": p_min,
                                "直近2週間のプレイ時間 (時間)": round(
                                    p_2w_min / 60, 1
                                ),
                            }
                        )

                    df = pd.DataFrame(game_list)
                    df = df.sort_values(
                        by="総プレイ時間 (分)", ascending=False
                    )

                    st.success(
                        f"合計 {len(df)} 件のゲームを取得しました！"
                    )

                    # 取得結果のプレビュー表示（上位10件）
                    st.dataframe(df.head(10), use_container_width=True)

                    # CSVデータの作成 (BOM付きUTF-8)
                    csv_bytes = df.to_csv(
                        index=False, encoding="utf-8-sig"
                    ).encode("utf-8-sig")

                    # ダウンロードボタン
                    st.download_button(
                        label="📥 CSVファイルをダウンロード",
                        data=csv_bytes,
                        file_name=f"steam_playtime_{steam_id}.csv",
                        mime="text/csv",
                    )
            else:
                st.error(
                    f"エラーが発生しました。(ステータスコード: {response.status_code}) Steam ID を確認してください。"
                )