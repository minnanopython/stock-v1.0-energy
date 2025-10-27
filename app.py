import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import timedelta
import numpy as np
import altair as alt
# --------------------------------------------------------------------------------------
# タイトルと枠組み
# --------------------------------------------------------------------------------------
st.set_page_config(
    page_title="Stock Comparison",
    page_icon=":chart_with_upwards_trend:",
    layout="wide",
)
st.markdown("# 📈 Stock Comparison")
st.markdown("---")
# --------------------------------------------------------------------------------------
# 銘柄に関する設定 (Daily Gainの対象銘柄)
# --------------------------------------------------------------------------------------
DEFAULT_SECTOR = "電設工事"
SECTORS = {
    "エネルギー資源": {
        '1605.T': 'ＩＮＰＥＸ',
        '1515.T': '日鉄鉱業',
        '1662.T': '石油資源開発',
        '5020.T': 'ＥＮＥＯＳホールディングス',
        '5019.T': '出光興産',
        '5021.T': 'コスモエネルギーホールディングス',
        '1514.T': '住石ホールディングス',
    },
    "主要電力": {
        '9501.T': '東京電力ホールディングス',
        '9502.T': '中部電力',
        '9503.T': '関西電力',
        '9504.T': '中国電力',
        '9505.T': '北陸電力',
        '9506.T': '東北電力',
        '9507.T': '四国電力',
        '9508.T': '九州電力',
        '9509.T': '北海道電力',
        '9513.T': '電源開発',
        '9511.T': '沖縄電力',
    },
    "電設工事": {
        '1942.T': '関電工',
        '1959.T': '九電工',
        '1944.T': 'きんでん',
        '1941.T': '中電工',
        '1949.T': '住友電設',
        '1930.T': '北陸電気工事',
        '1934.T': 'ユアテック',
        '1939.T': '四電工',
        '1946.T': 'トーエネック',
        '1945.T': '東京エネシス',
        '1950.T': '日本電設工業',
        '1938.T': '日本リーテック',
    },
    "通信工事": {
        '1417.T': 'ミライト・ワン',
        '1721.T': 'コムシスホールディングス',
        '1951.T': 'エクシオグループ',
    },
}
ALL_STOCKS_MAP = {ticker: name for sector in SECTORS.values() for ticker, name in sector.items()}
ALL_TICKERS_WITH_N225 = list(set(list(ALL_STOCKS_MAP.keys()) + ['^N225']))
def get_stock_name(ticker_code):
    if ticker_code == '^N225':
        return "日経平均"
    return ALL_STOCKS_MAP.get(ticker_code, ticker_code)
# --------------------------------------------------------------------------------------
# Auto Scale の Session State 初期化
# --------------------------------------------------------------------------------------
if "autoscale_enabled" not in st.session_state:
    st.session_state["autoscale_enabled"] = True
# --------------------------------------------------------------------------------------
# データ取得ヘルパー関数
# --------------------------------------------------------------------------------------
def _fetch_data(tickers_list, start_date, end_date, interval):
    if not tickers_list:
        return pd.DataFrame()
    unique_tickers = list(set(tickers_list))
    try:
        data = yf.download(
            tickers=unique_tickers,
            start=start_date,
            end=end_date,
            interval=interval,
            auto_adjust=True,
            progress=False
        )
        if 'Close' in data.columns.get_level_values(0):
            data_close = data["Close"]
        elif 'Close' in data.columns:
            data_close = data['Close'].to_frame(name=unique_tickers[0])
        else:
            return pd.DataFrame(index=pd.to_datetime([]), columns=unique_tickers)
    except yf.exceptions.YFRateLimitError as e:
        raise e
    except Exception as e:
        st.error(f"yfinanceデータ取得エラー ({interval}): {e}")
        return pd.DataFrame()
    data_close = data_close.sort_index()
    data_close_filled = data_close.ffill()
    if isinstance(data_close_filled.columns, pd.MultiIndex):
        if 'Close' in data_close_filled.columns.get_level_values(0):
            data_close_filled.columns = data_close_filled.columns.get_level_values(1)
    return data_close_filled.dropna(axis=0, how='all')
# --------------------------------------------------------------------------------------
# データ取得とキャッシュを行う関数
# --------------------------------------------------------------------------------------
MAX_YF_PERIOD = "5y"
MAX_YF_INTERVAL = "1wk"
@st.cache_data(show_spinner=True, ttl=timedelta(minutes=30))
def load_daily_data_cached(tickers_list, yf_period_str):
    """日次OHLCVデータを取得しキャッシュする関数"""
    if not tickers_list:
        return pd.DataFrame()
    unique_tickers = list(set(tickers_list))
    try:
        tickers_obj = yf.Tickers(unique_tickers)
        # High, Low, Open, Close, Volumeを含むOHLCVデータを取得
        data = tickers_obj.history(period="5y", interval="1d", auto_adjust=True)
        if len(unique_tickers) == 1 and 'Close' in data.columns:
            data.columns.name = 'Variable'
            data.columns = pd.MultiIndex.from_product([data.columns, unique_tickers], names=['Variable', 'Ticker'])
        return data.dropna(axis=0, how='all')
    except yf.exceptions.YFRateLimitError as e:
        raise e
    except Exception as e:
        st.error(f"yfinanceデータ取得エラー (日次): {e}")
        return pd.DataFrame()
@st.cache_data(show_spinner=True, ttl=timedelta(hours=6))
def load_all_data_cached(tickers_list):
    """週次終値データを取得しキャッシュする関数"""
    if not tickers_list:
        return pd.DataFrame()
    unique_tickers = list(set(tickers_list))
    try:
        tickers_obj = yf.Tickers(unique_tickers)
        data = tickers_obj.history(period=MAX_YF_PERIOD, interval=MAX_YF_INTERVAL, auto_adjust=True)
        if 'Close' in data.columns.get_level_values(0):
            data_close = data["Close"]
        elif len(unique_tickers) == 1 and 'Close' in data.columns:
            data_close = data["Close"].to_frame(name=unique_tickers[0])
        else:
            return pd.DataFrame(index=pd.to_datetime([]), columns=unique_tickers)
    except yf.exceptions.YFRateLimitError as e:
        raise e
    except Exception as e:
        st.error(f"yfinanceデータ取得エラー (週次): {e}")
        return pd.DataFrame()
    return data_close.dropna(axis=0, how='all').sort_index()
@st.cache_data(show_spinner=False, ttl=timedelta(hours=6))
def load_ticker_financials_cached(ticker_list):
    """財務指標を取得しキャッシュする関数"""
    financials = {}
    if not ticker_list:
        return {}
    stock_tickers = [t for t in ticker_list if t != '^N225']
    for ticker in stock_tickers:
        try:
            ticker_obj = yf.Ticker(ticker)
            info = ticker_obj.info
            per = info.get('forwardPE')
            pbr = info.get('priceToBook')
            eps = info.get('trailingEps')
            roe = info.get('returnOnEquity')
            if roe is not None:
                roe *= 100
            roa = info.get('returnOnAssets')
            if roa is not None:
                roa *= 100
            market_cap = info.get('marketCap')
            beta = info.get('beta')
            dividend_yield = info.get('dividendYield')
            fiscal_date_ending = info.get('fiscalDateEnding')

            financials[ticker] = {
                "PER": per,
                "PBR": pbr,
                "EPS": eps,
                "ROE": roe,
                "ROA": roa,
                "配当": dividend_yield,
            }
        except Exception:
            financials[ticker] = {
                "PER": None,
                "PBR": None,
                "EPS": None,
                "ROE": None,
                "ROA": None,
                "配当": None, 
            }
    return financials
# --------------------------------------------------------------------------------------
# 騰落率を計算する関数
# --------------------------------------------------------------------------------------
def calculate_gains(daily_data: pd.DataFrame, days: int) -> pd.Series:
    if daily_data.empty:
        return pd.Series(dtype=float)
    if isinstance(daily_data.columns, pd.MultiIndex):
        daily_price_data = daily_data['Close']
    else:
        daily_price_data = daily_data
        
    latest_prices = daily_price_data.iloc[-1].ffill()
    if len(daily_price_data) > days:
        previous_prices = daily_price_data.iloc[-(days + 1)].ffill()
    elif len(daily_price_data) > 0 and days >= 1:
        previous_prices = daily_price_data.iloc[0].ffill()
    else:
        return pd.Series(0, index=daily_price_data.columns)     
    gains = ((latest_prices - previous_prices) / previous_prices) * 100
    return gains.dropna()
def calculate_monthly_gain(daily_data: pd.DataFrame) -> pd.Series:
    if daily_data.empty:
        return pd.Series(dtype=float)
    if isinstance(daily_data.columns, pd.MultiIndex):
        daily_price_data = daily_data['Close']
    else:
        daily_price_data = daily_data
    start_prices = daily_price_data.iloc[0].ffill()
    latest_prices = daily_price_data.iloc[-1].ffill()
    gains = ((latest_prices - start_prices) / start_prices) * 100
    return gains.dropna()
def calculate_period_gain(daily_data: pd.DataFrame, start_date_str: str, end_date_str: str) -> pd.Series:
    """
    指定された開始日と終了日の間の騰落率を計算する。
    開始日と終了日は 'YYYY-MM-DD' 形式の文字列。
    指定日にデータがない場合は直前の営業日を採用。
    """
    if daily_data.empty:
        return pd.Series(dtype=float)
    if isinstance(daily_data.columns, pd.MultiIndex):
        daily_price_data = daily_data['Close']
    else:
        daily_price_data = daily_data
    try:
        start_price_series = daily_price_data.loc[:start_date_str].iloc[-1]
        end_price_series = daily_price_data.loc[:end_date_str].iloc[-1]
        valid_tickers = start_price_series.index.intersection(end_price_series.index)
        start_price = start_price_series[valid_tickers]
        end_price = end_price_series[valid_tickers]
        valid_for_calc = (start_price.notna()) & (end_price.notna()) & (start_price != 0)
        start_price_calc = start_price[valid_for_calc]
        end_price_calc = end_price[valid_for_calc]
        gains = ((end_price_calc - start_price_calc) / start_price_calc) * 100
        full_gains = pd.Series(np.nan, index=daily_price_data.columns)
        full_gains.update(gains)
        return full_gains
    except IndexError:
        return pd.Series(np.nan, index=daily_price_data.columns)
    except Exception:
        return pd.Series(np.nan, index=daily_price_data.columns)
def calculate_daily_returns_df(daily_price_data: pd.DataFrame) -> pd.DataFrame:
    if daily_price_data.empty:
        return pd.DataFrame()
    if isinstance(daily_price_data.columns, pd.MultiIndex):
        df_price = daily_price_data['Close']
    else:
        df_price = daily_price_data
    df_returns = df_price.pct_change() * 100
    return df_returns.dropna(how='all').iloc[-180:]
# --------------------------------------------------------------------------------------
# セクター選択変更時のコールバック関数
# --------------------------------------------------------------------------------------
def reset_stock_selection():
    st.session_state["_stock_selection_needs_reset"] = True
# --------------------------------------------------------------------------------------
# 選択ウィジェットの配置
# --------------------------------------------------------------------------------------
col_select_sector, col_select_stock = st.columns([1, 4])
with col_select_sector:
    st.markdown("セクター")
    sector_options = list(SECTORS.keys())
    default_sector_key = DEFAULT_SECTOR
    default_sectors = st.session_state.get("multiselect_sectors", [default_sector_key])
    selected_sectors = st.multiselect(
        "セクターを選択",
        options=sector_options,
        default=default_sectors,
        key="multiselect_sectors",
        label_visibility="collapsed",
        on_change=reset_stock_selection
    )
SELECTED_SECTOR_STOCKS_MAP = {}
if selected_sectors:
    for sector in selected_sectors:
        SELECTED_SECTOR_STOCKS_MAP.update(SECTORS.get(sector, {}))
else:
    SELECTED_SECTOR_STOCKS_MAP = ALL_STOCKS_MAP
stock_options = [name for name in SELECTED_SECTOR_STOCKS_MAP.values()]

all_current_stock_names = stock_options
if "multiselect_stocks" not in st.session_state:
    st.session_state["multiselect_stocks"] = all_current_stock_names
elif st.session_state.get("_stock_selection_needs_reset"):
    st.session_state["multiselect_stocks"] = all_current_stock_names
    del st.session_state["_stock_selection_needs_reset"]
else:
    current_selection = st.session_state["multiselect_stocks"]
    st.session_state["multiselect_stocks"] = [name for name in current_selection if name in all_current_stock_names]
with col_select_stock:
    st.markdown("銘柄")
    selected_stock_names = st.multiselect(
        "銘柄を選択",
        options=all_current_stock_names,
        key="multiselect_stocks",
        label_visibility="collapsed"
    )
FINAL_STOCKS_MAP = {}
name_to_ticker = {name: ticker for ticker, name in SELECTED_SECTOR_STOCKS_MAP.items()}
for name in selected_stock_names:
    ticker = name_to_ticker.get(name)
    if ticker:
        FINAL_STOCKS_MAP[ticker] = name
SELECTED_STOCKS_MAP = FINAL_STOCKS_MAP
selected_plot_tickers = list(SELECTED_STOCKS_MAP.keys())
# --------------------------------------------------------------------------------------
# データロードとキャッシュを実行、日次データ５年分、週次データ５年分
# --------------------------------------------------------------------------------------
data_raw_5y = pd.DataFrame()
try:
    with st.spinner(f"週次データをロード中..."):
        data_raw_5y = load_all_data_cached(ALL_TICKERS_WITH_N225)
    if data_raw_5y.empty:
        pass
except yf.exceptions.YFRateLimitError:
    st.warning("YFinanceの接続制限が発生しています。しばらくしてから再試行してください。")
    load_all_data_cached.clear()
    st.stop()
except Exception as e:
    st.error(f"データ読み込みエラー: {e}")
    st.stop()
daily_data_ohlcv = pd.DataFrame() # High, Low, Open, Close, Volume 全データ
try:
    with st.spinner(f"日次データをロード中..."):
        daily_data_ohlcv = load_daily_data_cached(ALL_TICKERS_WITH_N225, "5y") 
    if daily_data_ohlcv.empty:
        st.warning("日次データがロードできませんでした。騰落率の計算ができません。")
except yf.exceptions.YFRateLimitError:
    st.warning("YFinanceの接続制限が発生しています。しばらくしてから再試行してください。")
    load_daily_data_cached.clear()
except Exception as e:
    st.error(f"日次データ読み込みエラー: {e}")

# 騰落率計算用に終値のみを抽出
if not daily_data_ohlcv.empty and isinstance(daily_data_ohlcv.columns, pd.MultiIndex):
    daily_data_for_table = daily_data_ohlcv['Close'].ffill()
else:
    daily_data_for_table = daily_data_ohlcv
    
st.markdown(f"## 📋 Stock Gain")

ALL_FINANCIALS = {}
if SELECTED_SECTOR_STOCKS_MAP:
    try:
        with st.spinner("財務指標 (予想PER, PBR, EPS, ROE, ROA) をロード中..."):
            ALL_FINANCIALS = load_ticker_financials_cached(list(SELECTED_SECTOR_STOCKS_MAP.keys()))
    except yf.exceptions.YFRateLimitError:
        st.warning("YFinanceの接続制限が発生しています。しばらくしてから再試行してください。")
        load_ticker_financials_cached.clear()
    except Exception:
        pass
# --------------------------------------------------------------------------------------
# 騰落率の計算
# --------------------------------------------------------------------------------------
gain_1d = pd.Series(dtype=float)
gain_5d = pd.Series(dtype=float)
gain_1mo = pd.Series(dtype=float)
gain_3mo = pd.Series(dtype=float)
gain_6mo = pd.Series(dtype=float)
gain_1y = pd.Series(dtype=float)
gain_3y = pd.Series(dtype=float)
gain_5y = pd.Series(dtype=float)

# 仮の期間 (使用はしないがデータフレーム生成のために残す)
PERIOD_1_START = "2025-10-03"
PERIOD_1_END = "2025-10-06"
PERIOD_2_START = "2025-10-17"
PERIOD_2_END = "2025-10-20"

daily_returns_df = calculate_daily_returns_df(daily_data_for_table)
if not daily_data_for_table.empty:
    gain_1d = calculate_gains(daily_data_for_table, days=1)
    gain_5d = calculate_gains(daily_data_for_table, days=5)
    gain_1mo = calculate_monthly_gain(daily_data_for_table.iloc[-20:])
    gain_3mo = calculate_gains(daily_data_for_table, days=60)
    gain_6mo = calculate_gains(daily_data_for_table, days=120)
    gain_1y = calculate_gains(daily_data_for_table, days=250)
    gain_3y = calculate_gains(daily_data_for_table, days=750)
    gain_5y = calculate_gains(daily_data_for_table, days=1250)     
    gain_period1 = calculate_period_gain(daily_data_for_table, PERIOD_1_START, PERIOD_1_END)
    gain_period2 = calculate_period_gain(daily_data_for_table, PERIOD_2_START, PERIOD_2_END)
else:
    st.info("騰落率を計算するための日次データが取得できませんでした。")
# --------------------------------------------------------------------------------------
# データロードとテーブルの配置
# --------------------------------------------------------------------------------------
FILTERED_STOCKS = SELECTED_STOCKS_MAP
data_filtered_by_period = daily_data_for_table
df_results = pd.DataFrame() # ダウンロード機能のために初期化
ordered_display_df = pd.DataFrame() # テーブル配置修正のため初期化

# 騰落率の色付け関数
def color_gain(val):
    """騰落率に色を付ける関数"""
    if pd.isna(val):
        return ''
    try:
        val = float(val)
        color = '#008000' if val >= 0 else '#C70025'
        return f'color: {color}'
    except ValueError:
        return ''
        
if not data_filtered_by_period.empty and FILTERED_STOCKS:
    end_prices = data_filtered_by_period.iloc[-1].ffill()
    results = []
    GAIN_KEYS = {
        "1d": gain_1d,
        "5d": gain_5d,
        "1mo": gain_1mo,
        "3mo": gain_3mo,
        "6mo": gain_6mo,
        "1y": gain_1y,
        "3y": gain_3y,
        "5y": gain_5y,
    }
    for ticker, name in FILTERED_STOCKS.items():
        current_price = end_prices.get(ticker)
        stock_code = ticker.replace(".T", "")         
        row = {
            "コード": stock_code,
            "銘柄名": name,
            "株価": current_price,
        }         
        for key, gain_series in GAIN_KEYS.items():
            row[key] = gain_series.get(ticker)            
        row.update({
            "10/6": gain_period1.get(ticker), # 期間騰落率のデータは残す
            "10/20": gain_period2.get(ticker),
        })         
        financial_data = ALL_FINANCIALS.get(ticker, {})
        row.update({
            "予想PER": financial_data.get("PER"),
            "PBR": financial_data.get("PBR"),
            "EPS": financial_data.get("EPS"),
            "ROE": financial_data.get("ROE"),
            "ROA": financial_data.get("ROA"),
            "配当": financial_data.get("配当"),
        })         
        if current_price is not None:
            results.append(row)             
    
    if results:
        df_results = pd.DataFrame(results).sort_values("1d", ascending=False)
        display_df = df_results.copy()         
        
        def format_financial(x, col):
            """財務データを表示用にフォーマットする関数"""
            if x is None or pd.isna(x) or (isinstance(x, (float, int)) and (x < 0 or x == 0 and col in ["予想PER", "PBR"])):
                return "-"
            if col in ["予想PER", "PBR"] and x <= 0:
                return "-"
            if col in ["ROE", "ROA"]:
                return f"{x:.2f}" if x is not None else "-"
            elif col == "EPS":
                return f"{x:,.2f}"
            elif col == "配当":
                return f"{x:.2f}" if x is not None else "-"
            else:
                return f"{x:.2f}"             
        
        financial_cols_order = ["予想PER", "PBR", "EPS", "ROE", "ROA", "配当"]
        for col in financial_cols_order:
            display_df[col] = display_df[col].apply(lambda x: format_financial(x, col))
        
        gain_cols_period = list(GAIN_KEYS.keys())          
        final_cols = [
            "コード",
            "銘柄名",
            "株価",
            "配当", 
        ] + gain_cols_period + [
            "10/6",
            "10/20",
            "予想PER", "PBR", "EPS", "ROE", "ROA",
        ]          
        # 後で利用するため ordered_display_df に格納
        ordered_display_df = display_df[[col for col in final_cols if col in display_df.columns]]          
        
        gain_cols = gain_cols_period + ["10/6", "10/20"]
        num_rows = ordered_display_df.shape[0]
        ROW_HEIGHT = 35  
        HEADER_HEIGHT = 38 
        MAX_HEIGHT = 550 
        calculated_height = HEADER_HEIGHT + (num_rows * ROW_HEIGHT)
        table_height = min(calculated_height, MAX_HEIGHT) 
        
        # -----------------------------------------------
        # メインテーブルの作成・表示 (上部に配置)
        # -----------------------------------------------
        cols_table1 = [
            "コード",
            "銘柄名",
            "株価",
            "配当",
        ] + gain_cols_period + [
            "予想PER", "PBR", "EPS", "ROE", "ROA",
        ]
        df_table1 = ordered_display_df[[col for col in cols_table1 if col in ordered_display_df.columns]].copy()
        gain_cols_table1 = gain_cols_period 
        format_dict_table1 = {"株価": "{:,.2f}"}
        for col in gain_cols_table1:
            format_dict_table1[col] = "{:.2f}"             
        styled_df_table1 = df_table1.style.applymap(color_gain, subset=gain_cols_table1).format(
            format_dict_table1
        ).set_properties(**{'text-align': 'right'}, subset=["株価"] + gain_cols_table1)
        
        column_config_table1 = {
            "コード": st.column_config.TextColumn(width="small"),
            "銘柄名": st.column_config.TextColumn(width="small"),
            "株価": st.column_config.TextColumn(width="small"),
            "配当": st.column_config.TextColumn(width="small"),
            "予想PER": st.column_config.TextColumn(width="small"),
            "PBR": st.column_config.TextColumn(width="small"),
            "EPS": st.column_config.TextColumn(width="small"),
            "ROE": st.column_config.TextColumn(width="small"),
            "ROA": st.column_config.TextColumn(width="small"),
        }
        for col in gain_cols_table1:
            column_config_table1[col] = st.column_config.TextColumn(width="small")
        
        st.dataframe(
            data=styled_df_table1,
            height=table_height,
            column_config=column_config_table1,
            hide_index=True
        )
        
    else:
        st.info("選択された銘柄のデータがありませんでした。")
elif not selected_sectors:
    st.info("セクターを選択してください。")
elif daily_data_for_table.empty:
    st.info(f"有効な日次データが取得できませんでした。")
else:
    st.info("表示可能な銘柄がありませんでした。")
# --------------------------------------------------------------------------------------
# 期間に応じて週次データからデータを抽出するヘルパー関数
# --------------------------------------------------------------------------------------
def filter_data_by_period(data_raw_5y: pd.DataFrame, period_label: str) -> pd.DataFrame:
    if data_raw_5y.empty:
        return pd.DataFrame()
    end_date = data_raw_5y.index.max()  
    if period_label == "3ヶ月":
        start_date = end_date - timedelta(weeks=13)
    elif period_label == "6ヶ月":
        start_date = end_date - timedelta(weeks=26)
    elif period_label == "1年":
        start_date = end_date - timedelta(weeks=52)
    elif period_label == "3年":
        start_date = end_date - timedelta(weeks=52 * 3)
    elif period_label == "5年":
        start_date = data_raw_5y.index.min()
    else:
        return pd.DataFrame() 
    return data_raw_5y[data_raw_5y.index >= start_date]
# --------------------------------------------------------------------------------------
# 折れ線グラフの描画
# --------------------------------------------------------------------------------------
num_cols = 4
def create_and_display_charts(normalized_data, period_label, y_min_gain, y_max_gain, auto_scale=False):
    current_plot_tickers = [t for t in normalized_data.columns if t != '^N225']  
    if normalized_data.empty or current_plot_tickers == []:
        st.info(f"{period_label}のグラフを表示するためのデータがありません。") 
        return 
    if auto_scale:
        min_ratio = normalized_data.min().min() 
        max_ratio = normalized_data.max().max() 
        buffer = (max_ratio - min_ratio) * 0.1
        y_domain = [max(0.0, min_ratio - buffer), max_ratio + buffer]
    else:
        y_min_ratio = 1.0 + y_min_gain / 100.0
        y_max_ratio = 1.0 + y_max_gain / 100.0
        if y_min_ratio >= y_max_ratio:
            st.warning("⚠️ 最小目盛が最大目盛以上です。Y軸の範囲を±10%に設定しました。")
            y_domain = [1.0 - 0.10, 1.0 + 0.10] 
        else:
            y_domain = [y_min_ratio, y_max_ratio]          
    has_nikkei = '^N225' in normalized_data.columns
    nikkei_data = pd.DataFrame()
    if has_nikkei:
        nikkei_data = normalized_data[['^N225']].rename(columns={'^N225': 'Price'}).copy()
        nikkei_data['Date'] = nikkei_data.index
        nikkei_data['z_index'] = 0     
    date_range = normalized_data.index.max() - normalized_data.index.min()
    tick_count_val = 'auto'
    if period_label == "1日":
        x_format = "%H:%M"
        tick_count_val = 6
    elif period_label == "5日":
        x_format = "%d"
        tick_count_val = 5
    elif period_label == "1ヶ月":
        x_format = "%d"
        tick_count_val = 15
    elif date_range.days <= 400:
        x_format = "%m"
        tick_count_val = 'month' 
    else:
        x_format = "%Y"
        tick_count_val = 'year'  
    y_axis_config = alt.Axis( 
        title=None,
        labelExpr="datum.value == 1 ? '0.0' : format((datum.value - 1) * 100, '+.1f')"
    )
    for row_i in range((len(current_plot_tickers) + num_cols - 1) // num_cols):
        cols = st.columns(num_cols)
        for col_i in range(num_cols):
            idx = row_i * num_cols + col_i
            if idx < len(current_plot_tickers):
                ticker = current_plot_tickers[idx] 
                stock_data = pd.DataFrame({
                    "Date": normalized_data.index,
                    "Price": normalized_data[ticker],
                })
                stock_data['z_index'] = 1 
                combined_data = pd.concat([stock_data, nikkei_data]).dropna(subset=['Price'])       
                title_text = ticker[:4] + " " + get_stock_name(ticker) 
                base_chart = alt.Chart(combined_data).encode(
                    alt.X("Date:T", axis=alt.Axis(
                        format=x_format,
                        title=None,
                        labelAngle=0,
                        tickCount=tick_count_val
                    )),
                    alt.Y("Price:Q", 
                        scale=alt.Scale(zero=False, domain=y_domain),
                        axis=y_axis_config),
                ) 
                nikkei_line = alt.Chart(pd.DataFrame())
                if has_nikkei:
                    nikkei_line = base_chart.transform_filter(
                        alt.datum.z_index == 0
                    ).mark_line(
                        color="#A9A9A9",
                        strokeWidth=1.5
                    ).encode(
                        alt.Order("z_index:Q"),
                        tooltip=[
                            alt.Tooltip("Date:T", title="日付", format="%m/%d" if period_label in ["5日", "1ヶ月"] else x_format),
                            alt.Tooltip("Price:Q", title="日経騰落率", 
                                        format='+0.2') 
                        ]
                    ) 
                stock_line = base_chart.transform_filter(
                    alt.datum.z_index == 1
                    ).mark_line(
                    color="#C70025",
                    strokeWidth=2
                    ).encode(
                    alt.Order("z_index:Q"),
                    tooltip=[
                        alt.Tooltip("Date:T", title="日付", format="%m/%d" if period_label in ["5日", "1ヶ月"] else x_format),
                        alt.Tooltip("Price:Q", title=f"{title_text}騰落率", 
                                            format='+0.2')
                    ]
                    ) 
                chart = (
                    nikkei_line + stock_line
                ).properties(title=f"{title_text}", height=300, width='container')
                cell = cols[col_i].container(border=False)
                cell.altair_chart(chart, use_container_width=True)
# --------------------------------------------------------------------------------------
# 折れ線グラフの配置、３カ月以降は週次データでプロット
# --------------------------------------------------------------------------------------
st.markdown("---")
st.markdown("## 📈 Gain Chart") 
MIN_GAINS_FLAT = [-1, -3, -5, -7, -10, -12, -15, -20]
MAX_GAINS_FLAT = [+1, +3, +5, +7, +10, +12, +15, +20, 
                  +50, +70, +100, +200, +300, +500, +1000, +2000]
MIN_OPTIONS = [f"{g:.0f}" for g in MIN_GAINS_FLAT]
MAX_OPTIONS = [f"{g:+.0f}" for g in MAX_GAINS_FLAT]
def update_gain_value(key_to_check, key_to_update):
    current_value = st.session_state[key_to_check] 
    st.session_state[key_to_update] = current_value
def get_radio_index(options_list, key):
    selected_value = st.session_state.get(key)
    try:
        return options_list.index(selected_value)
    except ValueError:
        return None
col_charts, col, col_controls = st.columns([32, 0.1, 2.5])
with col_controls:
    autoscale_enabled = st.checkbox(
        "目盛",
        value=st.session_state["autoscale_enabled"],
        key="autoscale_checkbox"
    )
    st.session_state["autoscale_enabled"] = autoscale_enabled
    if not autoscale_enabled:
        with st.markdown("**最大目盛 (上限)**"): 
            max_default_value = "+1.0"
            if "selected_max_gain_value" not in st.session_state or st.session_state["selected_max_gain_value"] not in MAX_OPTIONS:
                st.session_state["selected_max_gain_value"] = max_default_value
            max_radio_key = "radio_y_max_gain_all"
            max_default_index = get_radio_index(MAX_OPTIONS, "selected_max_gain_value")     
            st.radio(
                "最大目盛",
                options=MAX_OPTIONS,
                index=max_default_index if max_default_index is not None else 0,
                key=max_radio_key,
                on_change=lambda: update_gain_value(max_radio_key, "selected_max_gain_value"),
                label_visibility="collapsed"
            )
        selected_max_text = st.session_state["selected_max_gain_value"]
        y_max_gain = float(selected_max_text.replace('+', ''))         
        with st.markdown("**最小目盛 (下限)**"): 
            min_default_value = "-1.0"
            if "selected_min_gain_value" not in st.session_state or st.session_state["selected_min_gain_value"] not in MIN_OPTIONS:
                st.session_state["selected_min_gain_value"] = min_default_value
            min_radio_key = "radio_y_min_gain_all"
            min_default_index = get_radio_index(MIN_OPTIONS, "selected_min_gain_value")     
            st.radio(
                "最小目盛",
                options=MIN_OPTIONS,
                index=min_default_index if min_default_index is not None else 0,
                key=min_radio_key,
                on_change=lambda: update_gain_value(min_radio_key, "selected_min_gain_value"),
                label_visibility="collapsed"
            )
        selected_min_text = st.session_state["selected_min_gain_value"]
        y_min_gain = float(selected_min_text)
    else:
        y_min_gain = -1.0
        y_max_gain = 1.0
CHART_Y_RANGE = {
    "1日": [y_min_gain, y_max_gain],
    "5日": [y_min_gain, y_max_gain],
    "1ヶ月": [y_min_gain, y_max_gain],
    "3ヶ月": [y_min_gain, y_max_gain],
    "6ヶ月": [y_min_gain, y_max_gain],
    "1年": [y_min_gain, y_max_gain],
    "3年": [y_min_gain, y_max_gain],
    "5年": [y_min_gain, y_max_gain],
}
with col_charts:
    if not selected_plot_tickers:
        st.info("グラフに表示する銘柄を上記マルチセレクトで選択してください。")
    elif data_raw_5y.empty or daily_data_for_table.empty:
        st.info("データがロードされていないため、グラフを表示できません。")
    else:
        plot_tickers = selected_plot_tickers[:]
        if '^N225' in data_raw_5y.columns and '^N225' not in plot_tickers:
            plot_tickers.append('^N225')     
        FIXED_PLOT_PERIODS = {
            "1ヶ月": {"period": "1ヶ月", "y_range": CHART_Y_RANGE["1ヶ月"], "data_source": "daily"},
            "1日": {"period": "1日", "y_range": CHART_Y_RANGE["1日"], "data_source": "daily"}, 
            "5日": {"period": "5日", "y_range": CHART_Y_RANGE["5日"], "data_source": "daily"},
            "3ヶ月": {"period": "3ヶ月", "y_range": CHART_Y_RANGE["3ヶ月"], "data_source": "weekly"}, 
            "6ヶ月": {"period": "6ヶ月", "y_range": CHART_Y_RANGE["6ヶ月"], "data_source": "weekly"}, 
            "1年": {"period": "1年", "y_range": CHART_Y_RANGE["1年"], "data_source": "weekly"},
            "3年": {"period": "3年", "y_range": CHART_Y_RANGE["3年"], "data_source": "weekly"},
            "5年": {"period": "5年", "y_range": CHART_Y_RANGE["5年"], "data_source": "weekly"},
        }  
        tabs = st.tabs(list(FIXED_PLOT_PERIODS.keys()))         
        for i, (period_label, config) in enumerate(FIXED_PLOT_PERIODS.items()):
            with tabs[i]:
                plot_data_raw = pd.DataFrame()
                if config["data_source"] == "daily":
                    if period_label == "1日":
                        plot_data_raw = daily_data_for_table.tail(2)
                    elif period_label == "5日":
                        plot_data_raw = daily_data_for_table.tail(6)
                    elif period_label == "1ヶ月":
                        plot_data_raw = daily_data_for_table.tail(22)
                    else:
                        plot_data_raw = daily_data_for_table
                else:
                    plot_data_raw = filter_data_by_period(data_raw_5y, config["period"])             
                plot_tickers_in_data = [t for t in plot_tickers if t in plot_data_raw.columns]              
                if plot_tickers_in_data and not plot_data_raw.empty and plot_data_raw.shape[0] >= 2:
                    plot_data_raw = plot_data_raw[plot_tickers_in_data].copy()
                    first_valid_price = plot_data_raw.iloc[0].copy()
                    valid_first_prices = first_valid_price[first_valid_price.index.isin(plot_data_raw.columns)].dropna()         
                    if not valid_first_prices.empty:
                        plot_data_raw = plot_data_raw[valid_first_prices.index].copy()
                        extracted_normalized = plot_data_raw / valid_first_prices          
                        y_min, y_max = config["y_range"] 
                        create_and_display_charts(
                            extracted_normalized, 
                            period_label, 
                            y_min, 
                            y_max,
                            auto_scale=st.session_state["autoscale_enabled"]
                        )
                    else:
                        st.info(f"選択された銘柄について「{period_label}」の有効なデータがありませんでした。")
                else:
                    st.info(f"選択された銘柄について「{period_label}」の有効なデータがありませんでした。")
# --------------------------------------------------------------------------------------
# 棒グラフの描画
# --------------------------------------------------------------------------------------
def create_and_display_bar_charts(daily_returns_data, filtered_stocks, selected_period_key, y_min_daily_gain=None, y_max_daily_gain=None):
    current_plot_tickers = [t for t in filtered_stocks.keys() if t in daily_returns_data.columns and t != '^N225']
    if daily_returns_data.empty or not current_plot_tickers:
        st.info(f"日ごとの騰落率グラフを表示するためのデータがありません。")
        return
    num_cols = 1
    y_domain = [y_min_daily_gain, y_max_daily_gain] if y_min_daily_gain is not None and y_max_daily_gain is not None else 'unaggregated'
    for row_i in range((len(current_plot_tickers) + num_cols - 1) // num_cols):
        cols = st.columns(num_cols)
        for col_i in range(num_cols):
            idx = row_i * num_cols + col_i
            if idx < len(current_plot_tickers):
                ticker = current_plot_tickers[idx]
                stock_name = ticker[:4] + " " + get_stock_name(ticker)
                plot_df = daily_returns_data[[ticker]].reset_index()
                plot_df.columns = ['Date', 'Daily_Return']
                plot_df['Color'] = plot_df['Daily_Return'].apply(lambda x: 'Positive' if x >= 0 else 'Negative')
                x_format = "%d"
                chart = alt.Chart(plot_df).mark_bar().encode(
                    alt.X("Date:T", axis=alt.Axis(
                        title=None,
                        format=x_format,
                        labelAngle=0
                    )),
                    alt.Y("Daily_Return:Q", axis=alt.Axis(title=None, format=".0f"),
                        scale=alt.Scale(domain=y_domain)
                    ),
                    alt.Color('Color:N',
                              scale=alt.Scale(domain=['Positive', 'Negative'], range=['#008000', '#C70025']),
                              legend=None),
                    tooltip=[
                        alt.Tooltip("Date:T", title="日付", format="%m/%d"),
                        alt.Tooltip("Daily_Return:Q", title="騰落率", format="+.2f")
                    ]
                ).properties(
                    title=f"{stock_name}",
                    height=250,
                    width='container'
                )
                cell = cols[col_i].container(border=False)
                cell.altair_chart(chart, use_container_width=True)
# --------------------------------------------------------------------------------------
# 棒グラフの配置
# --------------------------------------------------------------------------------------
MAX_GAINS_DAILY = [+1, +3, +5, +10, +15, +20]
MIN_GAINS_DAILY = [-1, -3, -5, -10, -15, -20]
MAX_OPTIONS_DAILY = [f"{g:+.0f}" for g in MAX_GAINS_DAILY]
MIN_OPTIONS_DAILY = [f"{g:.0f}" for g in MIN_GAINS_DAILY]
def find_closest_option(target_value, options_list_float):
    """目標値に最も近いオプションの値（float）を見つける"""
    if not options_list_float:
        return None
    abs_diff = np.abs(np.array(options_list_float) - target_value)
    closest_index = np.argmin(abs_diff)
    return options_list_float[closest_index]
df_daily_returns = calculate_daily_returns_df(daily_data_for_table)
if not df_daily_returns.empty and FILTERED_STOCKS:
    current_tickers = list(FILTERED_STOCKS.keys())
    plot_daily_returns = df_daily_returns[[t for t in current_tickers if t in df_daily_returns.columns]].copy()
    plot_daily_returns_filtered = plot_daily_returns.drop(columns=['^N225'], errors='ignore')
    if not plot_daily_returns_filtered.empty:
        st.markdown("---")
        st.markdown(f"## 📊 Daily Gain Chart 6mo")
        col_charts_daily, col_daily, col_controls_daily = st.columns([32, 0.1, 2.5])
        y_min_daily_calc = plot_daily_returns_filtered.min().min()
        y_max_daily_calc = plot_daily_returns_filtered.max().max()
        if not pd.isna(y_min_daily_calc) and not pd.isna(y_max_daily_calc):
            y_min_auto = y_min_daily_calc - 0.5 
            y_max_auto = y_max_daily_calc + 0.5
        else:
            y_min_auto, y_max_auto = None, None
        with col_controls_daily:
            autoscale_daily_enabled = st.checkbox(
                "目盛",
                value=st.session_state.get("autoscale_daily_enabled", True),
                key="autoscale_daily_checkbox"
            )
            st.session_state["autoscale_daily_enabled"] = autoscale_daily_enabled
            if not autoscale_daily_enabled:
                with st.markdown("**最大目盛 (上限)**"): 
                    max_default_value_float = MAX_GAINS_DAILY[0]
                    if y_max_auto is not None:
                        closest_max_float = find_closest_option(max(0.1, y_max_auto), MAX_GAINS_DAILY) 
                        max_default_value_float = closest_max_float                    
                    max_default_value = f"{max_default_value_float:+.1f}"
                    if "selected_max_daily_gain_value" not in st.session_state or st.session_state["selected_max_daily_gain_value"] not in MAX_OPTIONS_DAILY:
                        st.session_state["selected_max_daily_gain_value"] = max_default_value
                    max_radio_key_daily = "radio_y_max_gain_daily"
                    max_default_index_daily = get_radio_index(MAX_OPTIONS_DAILY, "selected_max_daily_gain_value") 
                    st.radio(
                        "最大目盛",
                        options=MAX_OPTIONS_DAILY,
                        index=max_default_index_daily if max_default_index_daily is not None else 0,
                        key=max_radio_key_daily,
                        on_change=lambda: update_gain_value(max_radio_key_daily, "selected_max_daily_gain_value"),
                        label_visibility="collapsed"
                    )
                selected_max_text_daily = st.session_state["selected_max_daily_gain_value"]
                y_max_daily_gain_set = float(selected_max_text_daily.replace('+', ''))
                with st.markdown("**最小目盛 (下限)**"): 
                    min_default_value_float = MIN_GAINS_DAILY[0] 
                    if y_min_auto is not None:
                        closest_min_float = find_closest_option(min(-0.1, y_min_auto), MIN_GAINS_DAILY)
                        min_default_value_float = closest_min_float                    
                    min_default_value = f"{min_default_value_float:.1f}"
                    if "selected_min_daily_gain_value" not in st.session_state or st.session_state["selected_min_daily_gain_value"] not in MIN_OPTIONS_DAILY:
                        st.session_state["selected_min_daily_gain_value"] = min_default_value          
                    min_radio_key_daily = "radio_y_min_gain_daily"
                    min_default_index_daily = get_radio_index(MIN_OPTIONS_DAILY, "selected_min_daily_gain_value") 
                    st.radio(
                        "最小目盛",
                        options=MIN_OPTIONS_DAILY,
                        index=min_default_index_daily if min_default_index_daily is not None else 0,
                        key=min_radio_key_daily,
                        on_change=lambda: update_gain_value(min_radio_key_daily, "selected_min_daily_gain_value"),
                        label_visibility="collapsed"
                    )
                selected_min_text_daily = st.session_state["selected_min_daily_gain_value"]
                y_min_daily_gain_set = float(selected_min_text_daily)         
            else:
                y_min_daily_gain_set = y_min_auto
                y_max_daily_gain_set = y_max_auto
        with col_charts_daily:
            filtered_stocks_only = {k: v for k, v in FILTERED_STOCKS.items() if k != '^N225'}  
            create_and_display_bar_charts(
                plot_daily_returns_filtered, 
                filtered_stocks_only, 
                "1ヶ月", 
                y_min_daily_gain_set, 
                y_max_daily_gain_set
            )         
    else:
        st.info("日ごとの騰落率棒グラフを表示するためのデータが不足しています。")
elif daily_data_for_table.empty:
    pass 
else:
    pass
    
# --------------------------------------------------------------------------------------
# 過去6ヶ月の日ごとの騰落率テーブルの追加 (修正版: 高さ自動調整と固定列)
# --------------------------------------------------------------------------------------
if 'plot_daily_returns_filtered' in locals() and not plot_daily_returns_filtered.empty and FILTERED_STOCKS:
    st.markdown("---")
    st.markdown("## 📅 過去6ヶ月 日ごと騰落率 (6mo Daily Gains)")
    df_daily_gains_T = plot_daily_returns_filtered.T
    df_daily_gains_T['コード'] = df_daily_gains_T.index.str.replace(".T", "")
    df_daily_gains_T['銘柄名'] = df_daily_gains_T.index.map(get_stock_name)
    cols = ['コード', '銘柄名'] + [col for col in df_daily_gains_T.columns if col not in ['コード', '銘柄名']]
    df_daily_gains_display = df_daily_gains_T[cols].copy()
    date_cols = df_daily_gains_display.columns[2:]
    date_format = "%m/%d"
    df_daily_gains_display.columns = ['コード', '銘柄名'] + [d.strftime(date_format) for d in date_cols]
    formatted_date_cols = df_daily_gains_display.columns[2:].tolist()
    format_dict = {col: "{:.2f}" for col in formatted_date_cols}
    styled_daily_gains = df_daily_gains_display.style.applymap(color_gain, subset=formatted_date_cols).format(
        format_dict
    ).set_properties(**{'text-align': 'right'}, subset=formatted_date_cols)
    num_rows = df_daily_gains_display.shape[0]
    ROW_HEIGHT = 35  
    HEADER_HEIGHT = 38 
    MAX_HEIGHT = 550
    calculated_height = HEADER_HEIGHT + (num_rows * ROW_HEIGHT)
    table_height = min(calculated_height, MAX_HEIGHT)
    column_config_daily = {
        "コード": st.column_config.TextColumn(width="small"),
        "銘柄名": st.column_config.TextColumn(width="small"),
    }
    st.dataframe(
        data=styled_daily_gains,
        height=table_height,
        use_container_width=True, 
        hide_index=True,
        column_config=column_config_daily
    )
# --------------------------------------------------------------------------------------
# ローソク足チャートの描画
# --------------------------------------------------------------------------------------
def create_and_display_candlestick_charts(ohlcv_data, filtered_stocks, period_label="6ヶ月"):
    """
    指定された期間のローソク足、日中変動幅、出来高チャートを縦に連結して表示する。
    """
    import altair as alt 
    import numpy as np 
    
    current_plot_tickers = [t for t in filtered_stocks.keys() if t != '^N225']
    if ohlcv_data.empty or not current_plot_tickers:
        st.info(f"{period_label}のローソク足グラフを表示するためのデータがありません。")
        return
    df_ohlcv = ohlcv_data.tail(126).copy()
    num_cols = 1 
    def get_stock_name(ticker):
        if 'SELECTED_STOCKS_MAP' in globals() and ticker in globals()['SELECTED_STOCKS_MAP']:
             return globals()['SELECTED_STOCKS_MAP'][ticker]
        return "銘柄名不明"
    for row_i in range((len(current_plot_tickers) + num_cols - 1) // num_cols):
        cols = st.columns(num_cols)
        for col_i in range(num_cols):
            idx = row_i * num_cols + col_i
            if idx < len(current_plot_tickers):
                ticker = current_plot_tickers[idx]             
                stock_name = ticker[:4] + " " + get_stock_name(ticker)             
                try:
                    df_plot = df_ohlcv.loc[:, (['Open', 'High', 'Low', 'Close', 'Volume'], ticker)].copy()
                    df_plot.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
                    df_plot.index.name = 'Date'
                    df_plot = df_plot.reset_index()
                except KeyError:
                    try:
                        if ticker in df_ohlcv.columns:
                            cols[col_i].info(f"{stock_name} ({ticker}) のOHLCVデータが不完全です。")
                            continue
                    except:
                           cols[col_i].info(f"{stock_name} ({ticker}) のOHLCVデータが見つかりません。")
                           continue
                df_plot['Color'] = np.where(df_plot['Close'] > df_plot['Open'], 'Positive', 'Negative')
                df_plot['Daily_Range'] = df_plot['High'] - df_plot['Low']
                candlestick_base = alt.Chart(df_plot).encode(
                    alt.X('Date:T', title=None, axis=alt.Axis(format="%m/%d", labelAngle=0))
                ).properties(title=f"{stock_name}", height=250)
                candlestick = candlestick_base.mark_bar().encode(
                    alt.Y('Open:Q', title=''),
                    alt.Y2('Close:Q'),
                    alt.Color('Color:N', scale=alt.Scale(domain=['Positive', 'Negative'], range=['#008000', '#C70025']), legend=None),
                    tooltip=[
                        alt.Tooltip('Date:T', title='日付', format="%m/%d"),
                        alt.Tooltip('Open:Q', title='始値', format=',.2f'),
                        alt.Tooltip('High:Q', title='高値', format=',.2f'),
                        alt.Tooltip('Low:Q', title='安値', format=',.2f'),
                        alt.Tooltip('Close:Q', title='終値', format=',.2f'),
                    ]
                )
                wick = candlestick_base.mark_rule().encode(
                    alt.Y('Low:Q'),
                    alt.Y2('High:Q'),
                    alt.Color('Color:N', scale=alt.Scale(domain=['Positive', 'Negative'], range=['#008000', '#C70025']), legend=None),
                )
                range_chart = alt.Chart(df_plot).mark_bar(opacity=0.4).encode(
                    alt.X('Date:T', title=None, axis=None), 
                    alt.Y('Daily_Range:Q', title='変動幅', axis=alt.Axis(titlePadding=5, format=',.1f')),
                    alt.Color('Color:N', scale=alt.Scale(domain=['Positive', 'Negative'], range=['#008000', '#C70025']), legend=None),
                    tooltip=[
                        alt.Tooltip('Date:T', title='日付', format="%m/%d"),
                        alt.Tooltip('Daily_Range:Q', title='日中変動幅', format=',.2f'),
                        alt.Tooltip('Color:N', title='終値-始値', format='')
                    ]
                ).properties(height=80)
                volume_chart = alt.Chart(df_plot).mark_bar(opacity=0.4).encode(
                    alt.X('Date:T', title=None, axis=None), 
                    alt.Y('Volume:Q', title='出来高', axis=alt.Axis(titlePadding=5, format=',d')), 
                    alt.Color('Color:N', scale=alt.Scale(domain=['Positive', 'Negative'], range=['#008000', '#C70025']), legend=None),
                    tooltip=[
                        alt.Tooltip('Date:T', title='日付', format="%m/%d"),
                        alt.Tooltip('Volume:Q', title='出来高', format=',d'),
                    ]
                ).properties(height=100)
                combined_ohlc = (candlestick + wick).encode(
                    alt.Y('Close:Q', scale=alt.Scale(zero=False))
                ).properties(height=250)

                chart = alt.VConcatChart(
                    vconcat=[
                        combined_ohlc,
                        range_chart,
                        volume_chart
                    ],
                ).resolve_scale(
                    x='shared',
                    y='independent'
                )
                cols[col_i].altair_chart(chart, use_container_width=True)
# --------------------------------------------------------------------------------------
# ローソク足チャートの配置
# --------------------------------------------------------------------------------------
if not daily_data_ohlcv.empty and FILTERED_STOCKS:
    st.markdown("---")
    st.markdown(f"## 📊 Daily Candlestick 6mo")
    filtered_stocks_only = {k: v for k, v in FILTERED_STOCKS.items() if k != '^N225'}
    create_and_display_candlestick_charts(
        daily_data_ohlcv,
        filtered_stocks_only, 
        period_label="6ヶ月"
    )
# --------------------------------------------------------------------------------------
# データダウンロード機能
# --------------------------------------------------------------------------------------
st.markdown("---")
st.markdown("## 📥 Download Data")

# 1. 全日次株価データ (OHLCV) のダウンロード
if not daily_data_ohlcv.empty and isinstance(daily_data_ohlcv.columns, pd.MultiIndex):
    # ダウンロード用にデータフレームをフラット化
    download_ohlcv_df = daily_data_ohlcv.stack(level=1).rename_axis(index=['Date', 'Ticker']).reset_index()
    download_ohlcv_df = download_ohlcv_df[['Date', 'Ticker', 'Open', 'High', 'Low', 'Close', 'Volume']]
    
    csv_data_ohlcv = download_ohlcv_df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="全日次株価データ (OHLCV) をCSVでダウンロード",
        data=csv_data_ohlcv,
        file_name='daily_stock_ohlcv.csv',
        mime='text/csv',
        help="高値(High)と安値(Low)を含む、全期間の始値、終値、出来高データです。"
    )
else:
    st.info("日次株価データ (OHLCV) が存在しないため、ダウンロードできません。")

# 2. 騰落率・財務指標テーブルのダウンロード
if 'df_results' in locals() and not df_results.empty:
    # ダウンロード用にデータフレームを準備 (表示用に文字列化したものとは別に、数値データを用意)
    download_df = df_results.copy()
    
    # 騰落率の小数点以下を整形し、データとして出力
    gain_cols_to_format = list(GAIN_KEYS.keys()) + ["10/6", "10/20"]
    for col in gain_cols_to_format:
        if col in download_df.columns:
            download_df[col] = download_df[col].round(2)
            
    # ダウンロード対象の列を選択
    download_cols = [
        "コード", "銘柄名", "株価", 
    ] + gain_cols_to_format + [
        "予想PER", "PBR", "EPS", "ROE", "ROA", "配当",
    ]
    download_df = download_df[[col for col in download_cols if col in download_df.columns]]
    
    csv_data_gains = download_df.to_csv(index=False, encoding='utf-8')
    st.download_button(
        label="騰落率・財務指標テーブルをCSVでダウンロード",
        data=csv_data_gains,
        file_name='stock_gains_and_financials.csv',
        mime='text/csv',
        help="表示されている騰落率と財務指標の結果テーブルです。"
    )
elif 'df_results' not in locals():
    st.info("騰落率テーブルデータが存在しないため、ダウンロードできません。")