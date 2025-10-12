# -*- coding: utf-8 -*-
import streamlit as st
import yfinance as yf
import pandas as pd
import altair as alt
from datetime import datetime, timedelta

# --- 定数 ---

SECTORS = {
    "11資源": {
        "5020.T": "5020 ＥＮＥＯＳホールディングス", "5019.T": "5019 出光興産",
        "5021.T": "5021 コスモエネルギーホールディングス", "1605.T": "1605 ＩＮＰＥＸ",
        "1662.T": "1662 石油資源開発", "8031.T": "8031 三井物産",
        "8058.T": "8058 三菱商事", "8001.T": "8001 伊藤忠商事",
        "8002.T": "8002 丸紅", "8053.T": "8053 住友商事",
        "8015.T": "8015 豊田通商", "2768.T": "2768 双日"
    },
    "12電力": {
        "9503.T": "9503 関西電力", "9502.T": "9502 中部電力",
        "9508.T": "9508 九州電力", "9506.T": "9506 東北電力",
        "9513.T": "9513 電源開発", "9507.T": "9507 四国電力",
        "9509.T": "9509 北海道電力", "9501.T": "9501 東京電力ホールディングス",
        "9504.T": "9504 中国電力", "9505.T": "9505 北陸電力",
        "9511.T": "9511 沖縄電力"
    },
    "13ガス": {
        "9531.T": "9531 東京瓦斯", "9532.T": "9532 大阪瓦斯",
        "9533.T": "9533 東邦瓦斯", "9551.T": "9551 メタウォーター",
        "9543.T": "9543 静岡ガス", "9536.T": "9536 西部ガスホールディングス",
        "9534.T": "9534 北海道瓦斯", "9539.T": "9539 京葉瓦斯",
        "9535.T": "9535 広島ガス", "9537.T": "9537 北陸瓦斯"
    },
    "14再エネ新電力": {
        "9519.T": "9519 レノバ", "9517.T": "9517 イーレックス",
        "3150.T": "3150 グリムス", "176A.T": "176A レジル",
        "350A.T": "350A デジタルグリッド", "7692.T": "7692 アースインフィニティ",
        "9514.T": "9514 エフオン"
    },
    "15燃料専門商社": {
        "8088.T": "8088 岩谷産業", "8020.T": "8020 兼松",
        "8078.T": "8078 阪和興業", "8133.T": "8133 伊藤忠エネクス",
        "5007.T": "5007 三愛オブリ", "3182.T": "3182 ミツウロコグループホールディングス",
        "8150.T": "8150 ＴＯＫＡＩホールディングス", "8084.T": "8084 三谷商事",
        "8103.T": "8103 明和産業", "8146.T": "8146 大丸エナウィン",
        "8037.T": "8037 カメイ", "8085.T": "8085 ナラサキ産業"
    },
}

ALL_SECTOR_TICKERS = list(set([t for d in SECTORS.values() for t in d.keys()]))
ALL_TICKERS_WITH_N225 = ALL_SECTOR_TICKERS + ['^N225']
DEFAULT_SECTOR_KEY = "11資源"
NUM_COLS = 6

# --- ユーティリティ関数 ---

def get_stock_name(ticker_code):
    """ティッカーコードに対応する銘柄名を取得する。"""
    if ticker_code == '^N225':
        return "日経平均"
    for sector_data in SECTORS.values():
        if ticker_code in sector_data:
            return sector_data[ticker_code]
    return ticker_code

def get_ticker_by_name(stock_name, sector_key):
    """銘柄名に対応するティッカーコードを取得する。"""
    current_sector_map = SECTORS.get(sector_key, {})
    for ticker, name in current_sector_map.items():
        if name == stock_name:
            return ticker
    return None

def reset_tickers_on_sector_change():
    """セクターが変更されたときに銘柄選択をデフォルトに戻すコールバック。"""
    selected_sector_key = st.session_state.selectbox_sector
    if 'selected_sector' not in st.session_state or selected_sector_key != st.session_state.selected_sector:
        st.session_state.selected_sector = selected_sector_key
        st.session_state.tickers_input = list(SECTORS[selected_sector_key].keys())

# --- Streamlit設定 ---

st.set_page_config(
    page_title="Energy Analysis v1",
    page_icon=":chart_with_upwards_trend:",
    layout="wide",
)
st.markdown("# :material/query_stats: Energy Stock Analysis")

# --- データ取得とキャッシュ (全銘柄 + N225) ---

@st.cache_data(show_spinner=False, ttl=timedelta(hours=6))
def load_all_data_cached(tickers_list):
    """全ての銘柄と日経平均の5年間のデータを一度に取得しキャッシュする。"""
    if not tickers_list:
        return pd.DataFrame() 
    unique_tickers = list(set(tickers_list)) 
    try:
        tickers_obj = yf.Tickers(unique_tickers)
        data = tickers_obj.history(period="5y") 
    except yf.exceptions.YFRateLimitError:
        raise
    except Exception as e:
        st.error(f"yfinanceデータ取得エラー: {e}")
        return pd.DataFrame()
    if data is None or data.empty:
        return pd.DataFrame(index=pd.to_datetime([]), columns=unique_tickers) 
    if 'Close' in data.columns.get_level_values(0):
        data_close = data["Close"]
    elif len(unique_tickers) == 1 and 'Close' in data.columns:
        data_close = data["Close"].to_frame(name=unique_tickers[0])
    else:
        return pd.DataFrame(index=pd.to_datetime([]), columns=unique_tickers) 
        
    return data_close.dropna(axis=0, how='all')

# 全データ取得の実行
try:
    with st.spinner("全データ (5年間) をロード中..."):
        data_5y_raw = load_all_data_cached(ALL_TICKERS_WITH_N225)     
    if data_5y_raw.empty:
        st.error("有効なデータが取得できませんでした。アプリケーションを再試行してください。")
        st.stop()
    TODAY = pd.Timestamp('today').normalize()    
except yf.exceptions.YFRateLimitError:
    st.warning("YFinanceの接続制限が発生しています。しばらくしてから再試行してください。")
    load_all_data_cached.clear()
    st.stop()
except Exception as e:
    st.error(f"データ読み込みエラー: {e}")
    st.stop()

# --- 状態管理と銘柄選択 ---

if "selected_sector" not in st.session_state:
    st.session_state.selected_sector = DEFAULT_SECTOR_KEY
if "tickers_input" not in st.session_state:
    st.session_state.tickers_input = list(SECTORS[DEFAULT_SECTOR_KEY].keys())
cols = st.columns([1, 3])
left_cell = cols[0].container(border=False)
right_cell = cols[1].container(border=False)
with left_cell:
    selected_sector_key = st.selectbox(
        "セクター", 
        options=list(SECTORS.keys()),
        index=list(SECTORS.keys()).index(st.session_state.selected_sector),
        label_visibility="collapsed",
        key="selectbox_sector",
        on_change=reset_tickers_on_sector_change
    )
with right_cell:
    current_sector_tickers_map = SECTORS[st.session_state.selected_sector]
    options = list(current_sector_tickers_map.values())
    default_options = [
        current_sector_tickers_map[t]
        for t in st.session_state.tickers_input
        if t in current_sector_tickers_map
    ]
    tickers_display = st.multiselect(
        "銘柄",
        options=options,
        default=default_options,
        placeholder="比較する銘柄を選択してください。",
        label_visibility="collapsed",
        key="multiselect_tickers_display" # キーを指定
    )
selected_tickers = [
    get_ticker_by_name(name, st.session_state.selected_sector) 
    for name in tickers_display
]
selected_tickers = [t for t in selected_tickers if t is not None]
st.session_state.tickers_input = selected_tickers
if not selected_tickers:
    st.info("比較する銘柄を選択してください。")
    st.stop()

# --- データスライスと前処理 ---

valid_tickers_for_analysis = [t for t in selected_tickers if t in data_5y_raw.columns] + ['^N225']
data_5y_subset = data_5y_raw[[c for c in valid_tickers_for_analysis if c in data_5y_raw.columns]]
data_1mo_raw = data_5y_subset[data_5y_subset.index >= (TODAY - pd.DateOffset(months=1))] 
data_1y_raw = data_5y_subset[data_5y_subset.index >= (TODAY - pd.DateOffset(years=1))] 
data_3y_raw = data_5y_subset[data_5y_subset.index >= (TODAY - pd.DateOffset(years=3))]
if data_1mo_raw.empty:
    st.error("選択された銘柄の有効なデータがありません。")
    st.stop()
def preprocess_and_normalize(data_raw, current_selected_tickers):
    """データの前処理（NaN処理、正規化）を行う。""" 
    if data_raw is None or data_raw.empty:
        return None, [] 
    all_target_tickers = [t for t in current_selected_tickers if t in data_raw.columns]
    if '^N225' in data_raw.columns and '^N225' not in all_target_tickers:
        all_target_tickers.append('^N225')    
    data = data_raw[all_target_tickers].copy()
    empty_columns = data.columns[data.isna().all()].tolist() 
    if empty_columns:
        st.warning(f"以下の銘柄のデータを取得できませんでした: {', '.join([get_stock_name(t) for t in empty_columns])}。グラフから除外します。")
        plot_tickers = [t for t in current_selected_tickers if t not in empty_columns]
        data = data.drop(columns=empty_columns, errors='ignore')
    else:
        plot_tickers = current_selected_tickers
    if data.empty:
        return None, plot_tickers
    normalized = data / data.iloc[0].bfill()
    return normalized, plot_tickers
normalized_1mo, confirmed_plot_tickers = preprocess_and_normalize(data_1mo_raw, selected_tickers)
normalized_1y, _ = preprocess_and_normalize(data_1y_raw, confirmed_plot_tickers)
normalized_3y, _ = preprocess_and_normalize(data_3y_raw, confirmed_plot_tickers)
plot_tickers_final = [t for t in confirmed_plot_tickers if t != '^N225']

# --- グラフ描画関数（X軸を工夫） ---

def create_and_display_charts(normalized_data, period_label):
    """
    正規化されたデータを用いて、指定された期間のグラフを描画する。
    period_labelに基づいてX軸の表示フォーマットを決定する。
    """
    current_plot_tickers = [t for t in normalized_data.columns if t != '^N225']
    if normalized_data is None or current_plot_tickers == []:
        st.info(f"{period_label}のグラフを表示するためのデータがありません。")
        return 
    st.markdown(f"#### 📈 株価変動 {period_label}") 
    has_nikkei = '^N225' in normalized_data.columns
    if has_nikkei:
        nikkei_data = normalized_data[['^N225']].rename(columns={'^N225': 'Price'})
        nikkei_data['Date'] = nikkei_data.index
        nikkei_data['z_index'] = 0
    else:
        nikkei_data = pd.DataFrame(columns=['Date', 'Price', 'z_index'])
    all_prices = normalized_data.values.flatten()
    valid_prices = all_prices[~pd.isna(all_prices)]
    min_price = valid_prices.min() if valid_prices.size > 0 else 0.8
    max_price = valid_prices.max() if valid_prices.size > 0 else 1.2
    y_domain = [min_price * 0.95, max_price * 1.05] 
    date_range = normalized_data.index.max() - normalized_data.index.min()
    if date_range.days <= 45:
        x_format = "%d"
    elif date_range.days <= 400:
        x_format = "%m"
    else:
        x_format = "%Y"        
    for row_i in range((len(current_plot_tickers) + NUM_COLS - 1) // NUM_COLS):
        cols = st.columns(NUM_COLS)
        for col_i in range(NUM_COLS):
            idx = row_i * NUM_COLS + col_i
            if idx < len(current_plot_tickers):
                ticker = current_plot_tickers[idx]
                stock_data = pd.DataFrame({
                    "Date": normalized_data.index,
                    "Price": normalized_data[ticker],
                })
                stock_data['z_index'] = 1 
                combined_data = pd.concat([stock_data, nikkei_data]).dropna(subset=['Price']) 
                title_text = get_stock_name(ticker) 
                base_chart = alt.Chart(combined_data).encode(
                    alt.X("Date:T", axis=alt.Axis(
                        format=x_format, 
                        title=None, 
                        labelAngle=0 
                    )),
                    alt.Y("Price:Q", axis=alt.Axis(title=None, format=".2f")).scale(zero=False, domain=y_domain),
                ) 
                if has_nikkei:
                    nikkei_line = base_chart.transform_filter(
                        alt.datum.z_index == 0
                    ).mark_line(
                        color="#A9A9A9", 
                        strokeWidth=1.5
                    ).encode(
                        alt.Order("z_index:Q"),
                        tooltip=[
                            alt.Tooltip("Date:T", title="日付"), 
                            alt.Tooltip("Price:Q", title="日経変動率", format=".2f")
                        ]
                    )
                else:
                    nikkei_line = alt.Chart(pd.DataFrame())
                stock_line = base_chart.transform_filter(
                    alt.datum.z_index == 1
                ).mark_line(
                    color="#C70025",
                    strokeWidth=2
                ).encode(
                    alt.Order("z_index:Q"),
                    tooltip=[
                        alt.Tooltip("Date:T", title="日付"), 
                        alt.Tooltip("Price:Q", title=f"{title_text}変動率", format=".2f")
                    ]
                ) 
                chart = (
                    nikkei_line + stock_line
                ).properties(title=f"{title_text}", height=300) 
                cell = cols[col_i].container(border=False)
                cell.altair_chart(chart, use_container_width=True) 
create_and_display_charts(normalized_1mo, "1ヶ月")
create_and_display_charts(normalized_1y, "1年")
create_and_display_charts(normalized_3y, "3年")

# --- カスタム期間選択機能 (株価変動率) ---

st.markdown("---")
st.markdown("### 🗓️ 株価変動率")
today_date = TODAY.date()
default_start_date_norm = today_date - timedelta(days=90) 
date_cols_norm = st.columns(2)
with date_cols_norm[0]:
    start_date_norm = st.date_input(
        "開始日", 
        value=default_start_date_norm, 
        max_value=today_date,
        key="custom_start_date_norm"
    )
with date_cols_norm[1]:
    end_date_norm = st.date_input(
        "終了日", 
        value=today_date, 
        max_value=today_date,
        key="custom_end_date_norm"
    )
if start_date_norm >= end_date_norm:
    st.warning("開始日は終了日よりも前に設定してください。(変動率グラフ)")
else:
    custom_data_raw_norm = data_5y_subset[
        (data_5y_subset.index.date >= start_date_norm) & 
        (data_5y_subset.index.date <= end_date_norm)
    ]
    
    if custom_data_raw_norm.empty:
        st.info("選択された期間に有効なデータがありませんでした。(変動率グラフ)")
    else:
        custom_normalized, _ = preprocess_and_normalize(custom_data_raw_norm, confirmed_plot_tickers)
        period_label_norm = f"{start_date_norm.strftime('%Y/%m/%d')} - {end_date_norm.strftime('%Y/%m/%d')}"
        if custom_normalized is not None:
            create_and_display_charts(custom_normalized, period_label_norm)

# --- 絶対値株価グラフの描画関数 ---

def create_absolute_price_chart(raw_data, period_label, selected_for_absolute):
    """
    絶対値の株価データを用いて、指定された期間のグラフを描画する。（複数銘柄比較用）
    """
    target_tickers = [t for t in selected_for_absolute if t in raw_data.columns and t != '^N225'] 
    if raw_data is None or not target_tickers:
        st.info(f"{period_label}の絶対値株価グラフを表示するためのデータがありません。")
        return 
    st.markdown(f"### 📈 株価推移 ({period_label})") 
    plot_data = raw_data[target_tickers].copy()
    plot_data['Date'] = plot_data.index
    melted_data = plot_data.melt(
        id_vars=['Date'],
        value_vars=target_tickers,
        var_name='Ticker',
        value_name='Price'
    ).dropna(subset=['Price'])
    melted_data['Name'] = melted_data['Ticker'].apply(get_stock_name)
    date_range = melted_data['Date'].max() - melted_data['Date'].min()
    if date_range.days <= 400:
        x_format = "%Y/%m/%d"
    else:
        x_format = "%Y/%m/%d"
    y_min = melted_data['Price'].min() * 0.95
    y_max = melted_data['Price'].max() * 1.05 
    base_chart = alt.Chart(melted_data).encode(
        x=alt.X("Date:T", axis=alt.Axis(
            format=x_format, 
            title=None,
            labelAngle=-90 
        )), 
        y=alt.Y("Price:Q", axis=alt.Axis(title="株価（円）", format=",")).scale(zero=False, domain=[y_min, y_max]),
        color=alt.Color("Name:N", title="銘柄"),
        tooltip=[
            alt.Tooltip("Date:T", title="日付"), 
            "Name", 
            alt.Tooltip("Price:Q", format=",", title="株価"), 
            "Ticker"
        ]
    ).properties(
        height=400,
    )
    chart = base_chart.mark_line()
    st.altair_chart(chart, use_container_width=True)

# --- 絶対値株価グラフ用のカスタム期間選択の追加 ---

st.markdown("---")
st.markdown("### 🗓️ 株価推移 (カスタム期間)")
absolute_options = [get_stock_name(t) for t in plot_tickers_final]
absolute_defaults = absolute_options
current_selected_map = {get_stock_name(t): t for t in plot_tickers_final}
selected_for_absolute_display = st.multiselect(
    "株価推移グラフに表示する銘柄",
    options=absolute_options,
    default=absolute_defaults,
    placeholder="表示する銘柄を選択してください。",
    key="absolute_multiselect_custom", 
    label_visibility="collapsed"
)
selected_for_absolute_tickers = [
    current_selected_map[name] for name in selected_for_absolute_display if name in current_selected_map
]
today_date = TODAY.date() # TODAYを使用
default_start_date_abs = today_date - timedelta(days=365) 
date_cols_abs = st.columns(2)
with date_cols_abs[0]:
    start_date_abs = st.date_input(
        "開始日", 
        value=default_start_date_abs, 
        max_value=today_date,
        key="custom_start_date_abs"
    )
with date_cols_abs[1]:
    end_date_abs = st.date_input(
        "終了日", 
        value=today_date, 
        max_value=today_date,
        key="custom_end_date_abs"
    )
if start_date_abs >= end_date_abs:
    st.warning("開始日は終了日よりも前に設定してください。(株価推移グラフ)")
else:
    custom_data_raw_abs = data_5y_subset[
        (data_5y_subset.index.date >= start_date_abs) & 
        (data_5y_subset.index.date <= end_date_abs)
    ]    
    if custom_data_raw_abs.empty:
        st.info("選択された期間に有効なデータがありませんでした。(株価推移グラフ)")
    else:
        period_label_abs = f"{start_date_abs.strftime('%Y/%m/%d')} - {end_date_abs.strftime('%Y/%m/%d')}"
        create_absolute_price_chart(custom_data_raw_abs, period_label_abs, selected_for_absolute_tickers)

# --- CSVダウンロード機能の追加 ---

def convert_df_to_csv(df):
    """Pandas DataFrameをCSV形式の文字列に変換する。"""
    return df.to_csv().encode('utf-8')

st.markdown("---") 
st.markdown("### 💾 全銘柄データダウンロード")
all_data_5y_for_download = data_5y_raw[[c for c in ALL_SECTOR_TICKERS if c in data_5y_raw.columns]]
if all_data_5y_for_download.empty:
    st.error("全銘柄の5年分データ取得に失敗したか、データが存在しませんでした。")
    csv_data = None
else:
    all_data_5y_for_download.columns = [get_stock_name(t) for t in all_data_5y_for_download.columns]
    csv_data = convert_df_to_csv(all_data_5y_for_download)
    today_str = datetime.now().strftime("%Y%m%d")
    download_filename = f"energy_stocks_5y_close_{today_str}.csv"
if csv_data:
    st.download_button(
        label="⬇️ 全銘柄 (5年分・終値) CSVダウンロード",
        data=csv_data,
        file_name=download_filename,
        mime="text/csv",
        help="SECTORSに定義されている全ての銘柄の過去5年間の終値データをダウンロードします。"
    )
else:
    st.warning("ダウンロード可能なデータが準備できませんでした。")

# --- コードの末尾 ---