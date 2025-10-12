# -*- coding: utf-8 -*-
import streamlit as st
import yfinance as yf
import pandas as pd
import altair as alt
from datetime import datetime

SECTORS = {
    "11資源": {
        "5020.T": "5020 ＥＮＥＯＳホールディングス",
        "5019.T": "5019 出光興産",
        "5021.T": "5021 コスモエネルギーホールディングス",
        "1605.T": "1605 ＩＮＰＥＸ",
        "1662.T": "1662 石油資源開発",
        "8031.T": "8031 三井物産",
        "8058.T": "8058 三菱商事",
        "8001.T": "8001 伊藤忠商事",
        "8002.T": "8002 丸紅",
        "8053.T": "8053 住友商事",
        "8015.T": "8015 豊田通商",
        "2768.T": "2768 双日"
    },
    "12電力": {
        "9503.T": "9503 関西電力",
        "9502.T": "9502 中部電力",
        "9508.T": "9508 九州電力",
        "9506.T": "9506 東北電力",
        "9513.T": "9513 電源開発",
        "9507.T": "9507 四国電力",
        "9509.T": "9509 北海道電力",
        "9501.T": "9501 東京電力ホールディングス",
        "9504.T": "9504 中国電力",
        "9505.T": "9505 北陸電力",
        "9511.T": "9511 沖縄電力"
    },
    "13ガス": {
        "9531.T": "9531 東京瓦斯",
        "9532.T": "9532 大阪瓦斯",
        "9533.T": "9533 東邦瓦斯",
        "9551.T": "9551 メタウォーター",
        "9543.T": "9543 静岡ガス",
        "9536.T": "9536 西部ガスホールディングス",
        "9534.T": "9534 北海道瓦斯",
        "9539.T": "9539 京葉瓦斯",
        "9535.T": "9535 広島ガス",
        "9537.T": "9537 北陸瓦斯"
    },
    "14再エネ新電力": {
        "9519.T": "9519 レノバ",
        "9517.T": "9517 イーレックス",
        "3150.T": "3150 グリムス",
        "176A.T": "176A レジル",
        "350A.T": "350A デジタルグリッド",
        "7692.T": "7692 アースインフィニティ",
        "9514.T": "9514 エフオン"
    },
    "15燃料専門商社": {
        "8088.T": "8088 岩谷産業",
        "8020.T": "8020 兼松",
        "8078.T": "8078 阪和興業",
        "8133.T": "8133 伊藤忠エネクス",
        "5007.T": "5007 三愛オブリ",
        "3182.T": "3182 ミツウロコグループホールディングス",
        "8150.T": "8150 ＴＯＫＡＩホールディングス",
        "8084.T": "8084 三谷商事",
        "8103.T": "8103 明和産業",
        "8146.T": "8146 大丸エナウィン",
        "8037.T": "8037 カメイ",
        "8085.T": "8085 ナラサキ産業"
    },
}
DEFAULT_SECTOR_KEY = "11資源"
DEFAULT_STOCKS = list(SECTORS[DEFAULT_SECTOR_KEY].keys())
NUM_COLS = 6
def get_stock_name(ticker_code):
    """ティッカーコードに対応する銘柄名を取得する。"""
    if ticker_code == '^N225':
        return "日経平均"
    for sector_data in SECTORS.values():
        if ticker_code in sector_data:
            return sector_data[ticker_code]
    return ticker_code
st.set_page_config(
    page_title="Energy Analysis v1",
    page_icon=":chart_with_upwards_trend:",
    layout="wide",
)
st.markdown("# :material/query_stats: Energy Stock Analysis")
if "selected_sector" not in st.session_state:
    st.session_state.selected_sector = DEFAULT_SECTOR_KEY
if "tickers_input" not in st.session_state:
    st.session_state.tickers_input = DEFAULT_STOCKS
cols = st.columns([1, 3])
left_cell = cols[0].container(border=False)
right_cell = cols[1].container(border=False)
with left_cell:
    selected_sector_key = st.selectbox(
        "セクター", 
        options=list(SECTORS.keys()),
        index=list(SECTORS.keys()).index(st.session_state.selected_sector),
        label_visibility="collapsed" 
    )
    if selected_sector_key != st.session_state.selected_sector:
        st.session_state.selected_sector = selected_sector_key
        st.session_state.tickers_input = list(SECTORS[selected_sector_key].keys())
with right_cell:
    current_sector_tickers_map = SECTORS[selected_sector_key]
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
        label_visibility="collapsed"
    )
selected_tickers = [
    t for t, name in current_sector_tickers_map.items() if name in tickers_display
]
st.session_state.tickers_input = selected_tickers
@st.cache_resource(show_spinner=False)
def load_all_data(tickers):
    """選択銘柄と日経平均の3年間のデータを一度に取得する。"""
    if not tickers:
        return pd.DataFrame() 
    all_tickers = tickers + ['^N225']
    unique_tickers = list(set(all_tickers)) 
    tickers_obj = yf.Tickers(unique_tickers)
    data = tickers_obj.history(period="3y") 
    if data is None or data.empty:
        return pd.DataFrame(index=pd.to_datetime([]), columns=unique_tickers) 
    if 'Close' in data.columns.get_level_values(0):
        data_close = data["Close"]
    elif len(unique_tickers) == 1 and 'Close' in data.columns:
        data_close = data["Close"].to_frame(name=unique_tickers[0])
    else:
        return pd.DataFrame(index=pd.to_datetime([]), columns=unique_tickers) 
    return data_close.dropna(axis=0, how='all')
try:
    if selected_tickers:
        with st.spinner("全データ (3年間) をロード中..."):
            data_3y_raw = load_all_data(selected_tickers) 
        if data_3y_raw.empty:
            st.error("有効なデータが取得できませんでした。")
            st.stop() 
        today = pd.Timestamp('today').normalize()
        one_month_ago = today - pd.DateOffset(months=1)
        data_1mo_raw = data_3y_raw[data_3y_raw.index >= one_month_ago] 
        one_year_ago = today - pd.DateOffset(years=1)
        data_1y_raw = data_3y_raw[data_3y_raw.index >= one_year_ago] 
        if data_1mo_raw.empty or data_1y_raw.empty or data_3y_raw.empty:
             raise RuntimeError("データスライス後に有効なデータがありませんでした。")
    else:
        st.info("比較する銘柄を選択してください。")
        st.stop() 
except yf.exceptions.YFRateLimitError:
    st.warning("YFinanceの接続制限が発生しています。しばらくしてから再試行してください。")
    load_all_data.clear()
    st.stop()
except Exception as e:
    st.error(f"データ読み込みエラー: {e}")
    st.stop()
def preprocess_and_normalize(data_raw, current_selected_tickers):
    """データの前処理（NaN処理、正規化）を行う。""" 
    if data_raw is None or data_raw.empty:
        return None, [] 
    empty_columns = data_raw.columns[data_raw.isna().all()].tolist() 
    if empty_columns:
        st.warning(f"以下の銘柄のデータを取得できませんでした: {', '.join([get_stock_name(t) for t in empty_columns])}。グラフから除外します。")
        plot_tickers = [t for t in current_selected_tickers if t not in empty_columns]
        data_raw = data_raw.drop(columns=empty_columns, errors='ignore')
    else:
        plot_tickers = current_selected_tickers

    if data_raw.empty and ('^N225' not in data_raw.columns or len(data_raw.columns) == 0):
        return None, plot_tickers
    normalized = data_raw / data_raw.iloc[0].bfill()
    return normalized, plot_tickers
normalized_1mo, confirmed_plot_tickers = preprocess_and_normalize(data_1mo_raw, selected_tickers)
if normalized_1mo is None:
    st.info("選択された銘柄の有効なデータがありません。")
    st.stop()
normalized_1y, _ = preprocess_and_normalize(data_1y_raw, selected_tickers)
normalized_3y, _ = preprocess_and_normalize(data_3y_raw, selected_tickers)
plot_tickers = [t for t in confirmed_plot_tickers if t != '^N225']
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
                if has_nikkei:
                    combined_data = pd.concat([stock_data, nikkei_data]).dropna(subset=['Price'])
                else:
                    combined_data = stock_data.dropna(subset=['Price']) 
                title_text = get_stock_name(ticker)
                if period_label == "1ヶ月":
                    y_domain = [0.9, 1.1] 
                    x_format = "%d"
                elif period_label == "1年":
                    y_domain = [0.5, 1.5]
                    x_format = "%m"
                elif period_label == "3年":
                    all_prices = normalized_data.values.flatten()
                    min_price = all_prices[~pd.isna(all_prices)].min() if all_prices[~pd.isna(all_prices)].size > 0 else 0.5
                    max_price = all_prices[~pd.isna(all_prices)].max() if all_prices[~pd.isna(all_prices)].size > 0 else 1.5
                    y_domain = [min_price * 0.9, max_price * 1.1] 
                    x_format = "%Y"
                else:
                    y_domain = [0.5, 1.5]
                    x_format = "%Y/%m" 
                base_chart = alt.Chart(combined_data).encode(
                    alt.X("Date:T", axis=alt.Axis(format=x_format, title=None)),
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
def create_absolute_price_chart(raw_data, period_label, selected_for_absolute):
    """
    絶対値の株価データを用いて、指定された期間のグラフを描画する。（複数銘柄比較用）
    """
    target_tickers = [t for t in selected_for_absolute if t in raw_data.columns and t != '^N225'] 
    if raw_data is None or not target_tickers:
        st.info(f"{period_label}の絶対値株価グラフを表示するためのデータがありません。")
        return 
    plot_data = raw_data[target_tickers].copy()
    plot_data['Date'] = plot_data.index
    melted_data = plot_data.melt(
        id_vars=['Date'],
        value_vars=target_tickers,
        var_name='Ticker',
        value_name='Price'
    ).dropna(subset=['Price'])
    melted_data['Name'] = melted_data['Ticker'].apply(get_stock_name)
    x_format = "%Y/%m" if period_label == "3年間" else "%Y/%m"
    y_min = melted_data['Price'].min() * 0.95
    y_max = melted_data['Price'].max() * 1.05 
    base_chart = alt.Chart(melted_data).encode(
        x=alt.X("Date:T", axis=alt.Axis(format=x_format, title=None)), 
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
absolute_options = [get_stock_name(t) for t in plot_tickers]
absolute_defaults = absolute_options
st.markdown("#### 📈 株価推移")
current_selected_map = {get_stock_name(t): t for t in plot_tickers}
selected_for_absolute_display = st.multiselect(
    "絶対値推移グラフに表示する銘柄",
    options=absolute_options,
    default=absolute_defaults,
    placeholder="表示する銘柄を選択してください。",
    key="absolute_multiselect",
    label_visibility="collapsed"
)
selected_for_absolute_tickers = [
    current_selected_map[name] for name in selected_for_absolute_display if name in current_selected_map
]
create_absolute_price_chart(data_3y_raw, "3年間", selected_for_absolute_tickers)