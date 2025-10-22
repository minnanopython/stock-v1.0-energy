import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import timedelta
import numpy as np
# Altairを追加
import altair as alt 

# --------------------------------------------------------------------------------------
# 💡タイトルと枠組み
# --------------------------------------------------------------------------------------
st.set_page_config(
    page_title="Daily Gain Viewer",
    page_icon=":chart_with_upwards_trend:",
    layout="wide",
)
st.markdown("# 📈 Daily Gain Viewer")
st.markdown("---")

# --------------------------------------------------------------------------------------
# 💡銘柄に関する設定 (Daily Gainの対象銘柄)
# --------------------------------------------------------------------------------------
SECTORS = {
    "エネルギー資源": {
        '5020.T': 'ＥＮＥＯＳホールディングス',
        '5019.T': '出光興産',
        '5021.T': 'コスモエネルギーホールディングス',
        '1605.T': 'ＩＮＰＥＸ',
        '1662.T': '石油資源開発',
        '1514.T': '住石ホールディングス',
        '1515.T': '日鉄鉱業',
    },
    "主要電力": {
        '9509.T': '北海道電力',
        '9506.T': '東北電力',
        '9501.T': '東京電力ホールディングス',
        '9502.T': '中部電力',
        '9505.T': '北陸電力',
        '9503.T': '関西電力',
        '9504.T': '中国電力',
        '9507.T': '四国電力',
        '9508.T': '九州電力',
        '9511.T': '沖縄電力',
        '9513.T': '電源開発',
    },
    "電工会社": {
        '1934.T': 'ユアテック',
        '1942.T': '関電工',
        '1941.T': '中電工',
        '1939.T': '四電工',
        '1959.T': '九電工',
        '1930.T': '北陸電気工事',
        '1946.T': 'トーエネック',
    },
}
ALL_STOCKS_MAP = {ticker: name for sector in SECTORS.values() for ticker, name in sector.items()}
ALL_TICKERS_WITH_N225 = list(set(list(ALL_STOCKS_MAP.keys()) + ['^N225']))

def get_stock_name(ticker_code):
    """ティッカーコードに対応する銘柄名を取得"""
    if ticker_code == '^N225':
        return "日経平均"
    return ALL_STOCKS_MAP.get(ticker_code, ticker_code)

# --------------------------------------------------------------------------------------
# 🌀データ取得ヘルパー関数
# --------------------------------------------------------------------------------------
def _fetch_data(tickers_list, start_date, end_date, interval):
    """yfinanceからデータを取得し、Close列を抽出する内部関数"""
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
# 🌀データ取得とキャッシュを行う関数 
# --------------------------------------------------------------------------------------
MAX_YF_PERIOD = "5y"
MAX_YF_INTERVAL = "1wk"

@st.cache_data(show_spinner=True, ttl=timedelta(minutes=30))
def load_daily_data_cached(tickers_list, yf_period_str):
    """日次データを取得してキャッシュ"""
    if not tickers_list:
        return pd.DataFrame()
    unique_tickers = list(set(tickers_list))
    try:
        tickers_obj = yf.Tickers(unique_tickers)
        data = tickers_obj.history(period=yf_period_str, interval="1d", auto_adjust=True) 
        if 'Close' in data.columns.get_level_values(0):
            data_close = data["Close"]
        elif len(unique_tickers) == 1 and 'Close' in data.columns:
            data_close = data["Close"].to_frame(name=unique_tickers[0])
        else:
            return pd.DataFrame(index=pd.to_datetime([]), columns=unique_tickers) 
    except yf.exceptions.YFRateLimitError as e:
        raise e
    except Exception as e:
        st.error(f"yfinanceデータ取得エラー (日次): {e}")
        return pd.DataFrame() 
    data_close = data_close.sort_index()
    data_close_filled = data_close.ffill() 
    return data_close_filled.dropna(axis=0, how='all')

#
# 5年分の週次データ取得してキャッシュ
# 
@st.cache_data(show_spinner=True, ttl=timedelta(hours=6))
def load_all_data_cached(tickers_list):
    """週次データを取得してキャッシュ"""
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

#
# 財務指標を取得してキャッシュ 
# 
@st.cache_data(show_spinner=False, ttl=timedelta(hours=6))
def load_ticker_financials_cached(ticker_list):
    """財務指標を取得してキャッシュ"""
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
            psr = info.get('priceToSales')
            beta = info.get('beta')
            div_yield = info.get('dividendYield')
            
            financials[ticker] = {
                "PER": per,
                "PBR": pbr,
                "EPS": eps, 
                "ROE": roe, 
                "ROA": roa, 
                "PSR": psr, 
                "Beta": beta, 
                "配当": div_yield
            }
        except Exception:
            financials[ticker] = {
                "PER": None,
                "PBR": None,
                "EPS": None,
                "ROE": None,
                "ROA": None,
                "PSR": None,
                "Beta": None,
                "配当": None
            }
    return financials

# --------------------------------------------------------------------------------------
# 🌀 騰落率を計算する関数 
# --------------------------------------------------------------------------------------
def calculate_gains(daily_data: pd.DataFrame, days: int) -> pd.Series:
    """指定された日数（営業日ベース）での騰落率を計算する。"""
    if daily_data.empty:
        return pd.Series(dtype=float)
    latest_prices = daily_data.iloc[-1].ffill() 
    if len(daily_data) > days:
        previous_prices = daily_data.iloc[-(days + 1)].ffill() 
    elif len(daily_data) > 0 and days >= 1:
        previous_prices = daily_data.iloc[0].ffill()
    else:
        return pd.Series(0, index=daily_data.columns)
    gains = ((latest_prices - previous_prices) / previous_prices) * 100
    return gains.dropna()

def calculate_monthly_gain(daily_data: pd.DataFrame) -> pd.Series:
    """データフレーム内の最初の営業日と最後の営業日の価格から期間の騰落率を計算する。"""
    if daily_data.empty:
        return pd.Series(dtype=float)
    start_prices = daily_data.iloc[0].ffill()
    latest_prices = daily_data.iloc[-1].ffill()
    gains = ((latest_prices - start_prices) / start_prices) * 100
    return gains.dropna()

# --- 新規追加: 日次騰落率を計算する関数 ---
def calculate_daily_returns_df(daily_price_data: pd.DataFrame) -> pd.DataFrame:
    """
    日次価格データから日ごとの騰落率（パーセント）を計算する。
    daily_returns_data に相当するDataFrameを生成する。
    """
    if daily_price_data.empty:
        return pd.DataFrame()
    df_returns = daily_price_data.pct_change() * 100
    return df_returns.dropna(how='all').iloc[-90:] #💡90日
# --------------------------------------------------------------------------------------

# --------------------------------------------------------------------------------------
# --- 棒グラフの描画 (新規追加)
# --------------------------------------------------------------------------------------
def create_and_display_bar_charts(daily_returns_data, filtered_stocks, selected_period_key, y_min_daily_gain=None, y_max_daily_gain=None): # Y軸のMin/Maxを追加
    """
    日ごとの騰落率データを用いて、銘柄ごとの棒グラフを描画する。
    daily_returns_data には、常に1ヶ月分のデータが渡されることを想定する。
    """
    # daily_returns_data のインデックス(日付)を列に変換し、ティッカー列を持つ
    current_plot_tickers = [t for t in filtered_stocks.keys() if t in daily_returns_data.columns] 	
    
    if daily_returns_data.empty or not current_plot_tickers: # [] ではなく not current_plot_tickers でチェック
        st.info(f"日ごとの騰落率グラフを表示するためのデータがありません。")
        return 	
    
    num_cols = 2 	

    # Y軸のスケールを定義（デフォルトまたはユーザー定義）
    # y_domain = [最小値, 最大値] または 'unaggregated'
    y_domain = [y_min_daily_gain, y_max_daily_gain] if y_min_daily_gain is not None and y_max_daily_gain is not None else 'unaggregated'
    
    # helper関数get_stock_nameはコード上部で定義済み
    
    for row_i in range((len(current_plot_tickers) + num_cols - 1) // num_cols):
        cols = st.columns(num_cols)
        for col_i in range(num_cols):
            idx = row_i * num_cols + col_i
            if idx < len(current_plot_tickers):
                ticker = current_plot_tickers[idx]
                stock_name = get_stock_name(ticker)
                
                # 棒グラフ用にデータを整形
                plot_df = daily_returns_data[[ticker]].reset_index()
                plot_df.columns = ['Date', 'Daily_Return']
                plot_df['Color'] = plot_df['Daily_Return'].apply(lambda x: 'Positive' if x >= 0 else 'Negative')
                
                # X軸のフォーマットは日次データに基づき「日」表示
                x_format = "%d" 
                
                chart = alt.Chart(plot_df).mark_bar().encode(
                    alt.X("Date:T", axis=alt.Axis(
                        title=None,
                        format=x_format,
                        labelAngle=0 
                    )),
                    alt.Y("Daily_Return:Q", axis=alt.Axis(title=None, format=".1f"),
                        scale=alt.Scale(domain=y_domain) # Y軸のスケールを適用
                    ), 
                    alt.Color('Color:N', 
                              scale=alt.Scale(domain=['Positive', 'Negative'], range=['#008000', '#C70025']),
                              legend=None),
                    tooltip=[
                        alt.Tooltip("Date:T", title="日付", format="%m/%d"), # ツールチップは月日表示
                        alt.Tooltip("Daily_Return:Q", title="騰落率", format=".2f")
                    ]
                ).properties(
                    title=f"{stock_name}",
                    height=250,
                    width='container'
                ) 	 	 	
                cell = cols[col_i].container(border=False)
                cell.altair_chart(chart, use_container_width=True)
# --------------------------------------------------------------------------------------


# --------------------------------------------------------------------------------------
# 🌀 セクター選択変更時のコールバック関数
# --------------------------------------------------------------------------------------
def reset_stock_selection():
    """セクター選択の変更時に銘柄選択を新しいセクターの全銘柄にリセットするフラグを設定"""
    st.session_state["_stock_selection_needs_reset"] = True

# --------------------------------------------------------------------------------------
# --- 🧩選択ウィジェットの配置 (目盛ウィジェットを除外)
# --------------------------------------------------------------------------------------
col_select_sector, col_select_stock = st.columns([1, 4]) 

#
# セクター選択ウィジェット
# 
with col_select_sector:
    st.markdown("セクター")
    sector_options = list(SECTORS.keys())
    default_sector_key = "メイン銘柄"
    # Session Stateに値があればそれを、なければデフォルトキーを選択
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

#
# 銘柄選択ウィジェットの Session State 初期化ロジック
#
all_current_stock_names = stock_options 
if "multiselect_stocks" not in st.session_state:
    st.session_state["multiselect_stocks"] = all_current_stock_names
elif st.session_state.get("_stock_selection_needs_reset"):
    st.session_state["multiselect_stocks"] = all_current_stock_names
    del st.session_state["_stock_selection_needs_reset"]
else:
    current_selection = st.session_state["multiselect_stocks"]
    st.session_state["multiselect_stocks"] = [name for name in current_selection if name in all_current_stock_names]

#
# 銘柄選択ウィジェット
# 
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
# 🧩データロードとキャッシュを実行
# --------------------------------------------------------------------------------------
#
# 5年の週次データ取得してキャッシュ
# 
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

#
# 3ヶ月の日次データ取得してキャッシュ
# 
daily_data_for_table = pd.DataFrame()
try:
    with st.spinner(f"日次データをロード中..."):
        daily_data_for_table = load_daily_data_cached(ALL_TICKERS_WITH_N225, "3mo") 
    if daily_data_for_table.empty:
        st.warning("日次データがロードできませんでした。騰落率の計算ができません。")
except yf.exceptions.YFRateLimitError:
    st.warning("YFinanceの接続制限が発生しています。しばらくしてから再試行してください。")
    load_daily_data_cached.clear()
except Exception as e:
    st.error(f"日次データ読み込みエラー: {e}")

#
# 財務指標を取得してキャッシュ
#
st.markdown(f"## 📋 Stock")
ALL_FINANCIALS = {}
if SELECTED_SECTOR_STOCKS_MAP:
    try:
        with st.spinner("財務指標 (予想PER, PBR, EPS, ROE, ROA, PSR, Beta, 配当利回り) をロード中..."):
            ALL_FINANCIALS = load_ticker_financials_cached(list(SELECTED_SECTOR_STOCKS_MAP.keys()))
    except yf.exceptions.YFRateLimitError:
        st.warning("YFinanceの接続制限が発生しています。しばらくしてから再試行してください。")
        load_ticker_financials_cached.clear()
    except Exception:
        pass

# --------------------------------------------------------------------------------------
# 🧩騰落率の計算
# --------------------------------------------------------------------------------------
gain_1d = pd.Series(dtype=float)
gain_5d = pd.Series(dtype=float)
gain_1mo = pd.Series(dtype=float) 
if not daily_data_for_table.empty:
    gain_1d = calculate_gains(daily_data_for_table, days=1)
    gain_5d = calculate_gains(daily_data_for_table, days=5)
    gain_1mo = calculate_monthly_gain(daily_data_for_table) 
else:
    st.info("騰落率を計算するための日次データが取得できませんでした。")

# --------------------------------------------------------------------------------------
# 🧩データロードとテーブルの配置
# --------------------------------------------------------------------------------------
FILTERED_STOCKS = SELECTED_STOCKS_MAP 
data_filtered_by_period = daily_data_for_table 
if not data_filtered_by_period.empty and FILTERED_STOCKS: 
    end_prices = data_filtered_by_period.iloc[-1].ffill()
    results = [] 	 	 	
    for ticker, name in FILTERED_STOCKS.items():
        current_price = end_prices.get(ticker)
        stock_code = ticker.replace(".T", "") 
        gain_1d_val = gain_1d.get(ticker)
        gain_5d_val = gain_5d.get(ticker)
        gain_1mo_val = gain_1mo.get(ticker)
        main_gain_percent = gain_1d_val 	 	 	
        financial_data = ALL_FINANCIALS.get(ticker, {})
        per = financial_data.get("PER") 
        pbr = financial_data.get("PBR")
        eps = financial_data.get("EPS")
        roe = financial_data.get("ROE")
        roa = financial_data.get("ROA")
        psr = financial_data.get("PSR")
        beta = financial_data.get("Beta")
        div_yield = financial_data.get("配当") 	 	
        if current_price is not None: 	 	 	
            results.append({
                "コード": stock_code, 
                "銘柄名": name,
                "株価": current_price, 	 	 	 	 
                "騰落率1d": gain_1d_val,
                "騰落率5d": gain_5d_val,
                "騰落率1mo": gain_1mo_val, 	 	 	 	 
                "騰落率": main_gain_percent, 
                "予想PER": per,
                "PBR": pbr,
                "EPS": eps,
                "ROE": roe,
                "ROA": roa,
                "PSR": psr,
                "Beta": beta, 
                "配当": div_yield 
            }) 	 	 	 
    if results:
        df_results = pd.DataFrame(results).sort_values("騰落率1d", ascending=False)
        display_df = df_results.copy() 	 	 	 
        def format_gain(x):
            if pd.isna(x):
                return "-"
            return f"{x:+.2f}" 	 	 	
        display_df["騰落率1d"] = display_df["騰落率1d"].apply(format_gain)
        display_df["騰落率5d"] = display_df["騰落率5d"].apply(format_gain)
        display_df["騰落率1mo"] = display_df["騰落率1mo"].apply(format_gain)
        display_df["株価"] = display_df["株価"].apply(lambda x: f"{x:,.2f}") 
        display_df.drop(columns=["騰落率"], inplace=True) 
        def format_financial(x, col):
            if not isinstance(x, (float, int)) or x is None or pd.isna(x):
                return "-"
            if col in ["予想PER", "PBR", "PSR"] and x <= 0:
                return "-"
            if col == "配当":
                    # 配当利回りはパーセント表示として、元の値が小数 (0.02) の場合は 100 倍して表示
                    return f"{x * 100:.2f}" if x is not None and x <= 1 else f"{x:.2f}"
            elif col in ["ROE", "ROA"]:
                    # ROE/ROAは既にパーセント表示のはず
                    return f"{x:.2f}" if x is not None else "-"
            else:
                return f"{x:.2f}" 	 	 	 
        financial_cols_order = ["予想PER", "PBR", "EPS", "ROE", "ROA", "PSR", "Beta", "配当"]
        for col in financial_cols_order:
            display_df[col] = display_df[col].apply(lambda x: format_financial(x, col)) 	 	 	 	
        final_cols = [
            "コード", 
            "銘柄名",
            "株価", 
            "騰落率1d", 
            "騰落率5d",
            "騰落率1mo", 
            "予想PER", "PBR", "EPS", "ROE", "ROA", "PSR", "Beta",
            "配当"
        ]
        ordered_display_df = display_df[final_cols] 	 	 	 	
        column_config = {
            "コード": st.column_config.TextColumn(width="small"),
            "銘柄名": st.column_config.TextColumn(width="small"),
            "株価": st.column_config.TextColumn(width="small"),
            "騰落率1d": st.column_config.TextColumn(width="small"),
            "騰落率5d": st.column_config.TextColumn(width="small"),
            "騰落率1mo": st.column_config.TextColumn(width="small"),
            "予想PER": st.column_config.TextColumn(width="small"),
            "PBR": st.column_config.TextColumn(width="small"),
            "EPS": st.column_config.TextColumn(width="small"), 
            "ROE": st.column_config.TextColumn(width="small"),
            "ROA": st.column_config.TextColumn(width="small"), 
            "PSR": st.column_config.TextColumn(width="small"), 
            "Beta": st.column_config.TextColumn(width="small"), 
            "配当": st.column_config.TextColumn(width="small"),
        } 
        st.dataframe(
            data=ordered_display_df,
            height=450,
            column_config=column_config,
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


# ======================================================================================
# --- グラフ描画ロジック (折れ線グラフ)
# ======================================================================================

# --------------------------------------------------------------------------------------
# 🌀 期間に応じて週次データからデータを抽出するヘルパー関数
# --------------------------------------------------------------------------------------
def filter_data_by_period(data_raw_5y: pd.DataFrame, period_label: str) -> pd.DataFrame:
    """期間ラベルに基づいて週次データをフィルタリングする。"""
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
        start_date = data_raw_5y.index.min() # 既に5年分で取得済み
    else:
        return pd.DataFrame() 

    # 期間の最初の営業日のデータからフィルタリング
    return data_raw_5y[data_raw_5y.index >= start_date]

# --------------------------------------------------------------------------------------
# --- 折れ線グラフの描画 (既存)
# --------------------------------------------------------------------------------------
num_cols = 6
def create_and_display_charts(normalized_data, period_label, y_min_gain, y_max_gain, auto_scale=False):
    """
    正規化されたデータを用いて、指定された期間のグラフを描画する。
    """
    current_plot_tickers = [t for t in normalized_data.columns if t != '^N225']
    
    if normalized_data.empty or current_plot_tickers == []:
        st.info(f"{period_label}のグラフを表示するためのデータがありません。")
        return 	
    
    # Y軸の範囲を設定
    if auto_scale:
        min_ratio = normalized_data.min().min() 
        max_ratio = normalized_data.max().max() 
        buffer = (max_ratio - min_ratio) * 0.1
        y_domain = [max(0.0, min_ratio - buffer), max_ratio + buffer]
    else:
        y_min_ratio = 1.0 + y_min_gain / 100.0
        y_max_ratio = 1.0 + y_max_gain / 100.0
        if y_min_ratio >= y_max_ratio:
            st.warning("最小目盛が最大目盛以上です。Y軸の範囲を±10%に設定しました。")
            y_domain = [1.0 - 0.10, 1.0 + 0.10] 
        else:
            y_domain = [y_min_ratio, y_max_ratio] 	 	 	
            
    has_nikkei = '^N225' in normalized_data.columns
    nikkei_data = pd.DataFrame()
    if has_nikkei:
        nikkei_data = normalized_data[['^N225']].rename(columns={'^N225': 'Price'}).copy()
        nikkei_data['Date'] = nikkei_data.index
        nikkei_data['z_index'] = 0 # 日経平均は背面 (0)
        
    date_range = normalized_data.index.max() - normalized_data.index.min() 
    
    # X軸フォーマットの設定
    if period_label in ["1日", "5日", "1ヶ月"]: 
        x_format = "%d"
    elif date_range.days <= 400:
        x_format = "%m"
    else:
        x_format = "%Y"
    y_axis_config = alt.Axis( 
        title=None,
        labelExpr="datum.value == 1 ? '0.0' : format((datum.value - 1) * 100, '+.1f')"
    )
    
    # グラフをタイル状に配置
    for row_i in range((len(current_plot_tickers) + num_cols - 1) // num_cols):
        cols = st.columns(num_cols)
        for col_i in range(num_cols):
            idx = row_i * num_cols + col_i
            if idx < len(current_plot_tickers):
                ticker = current_plot_tickers[idx] 	 	 	
                
                # 銘柄データ (z_index=1)
                stock_data = pd.DataFrame({
                    "Date": normalized_data.index,
                    "Price": normalized_data[ticker],
                })
                stock_data['z_index'] = 1 	 	 	
                
                # 銘柄と日経平均のデータを結合 (あれば)
                combined_data = pd.concat([stock_data, nikkei_data]).dropna(subset=['Price']) 
                
                title_text = get_stock_name(ticker) 	 	 	
                
                # ベースチャート
                base_chart = alt.Chart(combined_data).encode(
                    alt.X("Date:T", axis=alt.Axis(
                        format=x_format,
                        title=None,
                        labelAngle=0
                    )),
                    alt.Y("Price:Q", 
                        scale=alt.Scale(zero=False, domain=y_domain),
                        axis=y_axis_config),
                ) 	 	 	
                
                # 日経平均のライン (z_index=0)
                nikkei_line = alt.Chart(pd.DataFrame())
                if has_nikkei:
                    nikkei_line = base_chart.transform_filter(
                        alt.datum.z_index == 0
                    ).mark_line(
                        color="#A9A9A9", # 灰色
                        strokeWidth=1.5
                    ).encode(
                        alt.Order("z_index:Q"),
                        tooltip=[
                            alt.Tooltip("Date:T", title="日付", format=x_format),
                            alt.Tooltip("Price:Q", title="日経騰落率", 
                                        format='+0.2') 
                        ]
                    ) 	 	 	
                    
                # 銘柄のライン (z_index=1)
                stock_line = base_chart.transform_filter(
                    alt.datum.z_index == 1
                    ).mark_line(
                    color="#C70025", # 赤
                    strokeWidth=2
                    ).encode(
                    alt.Order("z_index:Q"),
                    tooltip=[
                        alt.Tooltip("Date:T", title="日付", format=x_format),
                        alt.Tooltip("Price:Q", title=f"{title_text}騰落率", 
                                    format='+0.2')
                    ]
                    ) 	 	 	
                    
                # グラフの結合と表示
                chart = (
                    nikkei_line + stock_line
                ).properties(title=f"{title_text}", height=300, width='container')
                cell = cols[col_i].container(border=False)
                cell.altair_chart(chart, use_container_width=True)


# --------------------------------------------------------------------------------------
# 🌟 騰落率グラフの配置 (目盛りの設定)
# --------------------------------------------------------------------------------------
st.markdown("---")
st.markdown("## 📈 Gain Chart") 

# --- 目盛りの値の定義 ---
MIN_GAINS_FLAT = [-1.0, -3.0, -5.0, -7.0, -10.0, -12.0, -15.0, -20.0]
MAX_GAINS_FLAT = [+1.0, +3.0, +5.0, +7.0, +10.0, +12.0, +15.0, +20.0, 
                  +50.0, +70.0, +100.0, +200.0, +300.0, +500.0, +1000.0, +2000.0]

# ラジオボタンのオプションとして、パーセント表記の文字列に変換
MIN_OPTIONS = [f"{g:.1f}" for g in MIN_GAINS_FLAT]
MAX_OPTIONS = [f"{g:+.1f}" for g in MAX_GAINS_FLAT] # +符号を追加

# --- 目盛り選択ロジックのヘルパー関数 ---
def update_gain_value(key_to_check, key_to_update):
    """選択されたラジオボタンの値を共通の Session State に保存する"""
    current_value = st.session_state[key_to_check] 
    st.session_state[key_to_update] = current_value
        
def get_radio_index(options_list, key):
    """共通の選択値に基づいて、現在のラジオボタンの初期インデックスを計算する"""
    selected_value = st.session_state.get(key)
    try:
        # 共通の選択値が現在のラジオボタンのオプションに含まれていればそのインデックスを返す
        return options_list.index(selected_value)
    except ValueError:
        # 含まれていない場合は、None を返す
        return None

# --- 目盛りの選択ウィジェット ---
# レイアウト: 最小目盛 (2列), 最大目盛 (4列), スペース
col_min_scale, col_max_scale, _ = st.columns([1, 2, 3]) 

# --- 最小目盛 (2列に分割して配置) ---
with col_min_scale:
    st.markdown("最小目盛")
    
    # MIN_OPTIONSを2列に分割
    min_half_index = len(MIN_OPTIONS) // 2
    min_options_col1 = MIN_OPTIONS[:min_half_index]
    min_options_col2 = MIN_OPTIONS[min_half_index:]

    # 2列のサブカラムを作成
    min_sub_col1, min_sub_col2 = st.columns(2)
    

    min_default_value = "-1.0"
    if "selected_min_gain_value" not in st.session_state or st.session_state["selected_min_gain_value"] not in MIN_OPTIONS:
        st.session_state["selected_min_gain_value"] = min_default_value

    # 1列目のラジオボタン
    min_radio1_key = "radio_y_min_gain_col1"
    min_radio1_default_index = get_radio_index(min_options_col1, "selected_min_gain_value")
    
    with min_sub_col1:
        st.radio(
            "最小目盛 (列1)",
            options=min_options_col1,
            # 共通の選択値が現在のリストにあればそのインデックス、なければリストの最初の要素をデフォルトにする
            index=min_radio1_default_index if min_radio1_default_index is not None else 0,
            key=min_radio1_key,
            on_change=lambda: update_gain_value(min_radio1_key, "selected_min_gain_value"),
            label_visibility="collapsed"
        )

    # 2列目のラジオボタン
    min_radio2_key = "radio_y_min_gain_col2"
    min_radio2_default_index = get_radio_index(min_options_col2, "selected_min_gain_value")
    
    with min_sub_col2:
        st.radio(
            "最小目盛 (列2)",
            options=min_options_col2,
            # 共通の選択値が現在のリストにあればそのインデックス、なければリストの最初の要素をデフォルトにする
            index=min_radio2_default_index if min_radio2_default_index is not None else 0,
            key=min_radio2_key,
            on_change=lambda: update_gain_value(min_radio2_key, "selected_min_gain_value"),
            label_visibility="collapsed"
        )
    
    # 最終的な最小目盛の値
    selected_min_text = st.session_state["selected_min_gain_value"]
    y_min_gain = float(selected_min_text.replace('', ''))

# --- 最大目盛 (4列に分割して配置) ---
with col_max_scale:
    st.markdown("最大目盛")
    
    # MAX_OPTIONSを4列に分割 (各4要素)
    max_options_col1 = MAX_OPTIONS[0:4]
    max_options_col2 = MAX_OPTIONS[4:8]
    max_options_col3 = MAX_OPTIONS[8:12]
    max_options_col4 = MAX_OPTIONS[12:16]

    max_sub_col1, max_sub_col2, max_sub_col3, max_sub_col4 = st.columns(4) 	 	
    max_default_value = "+1.0"
    if "selected_max_gain_value" not in st.session_state or st.session_state["selected_max_gain_value"] not in MAX_OPTIONS:
        st.session_state["selected_max_gain_value"] = max_default_value

    # ラジオボタンのリスト
    max_cols = [max_sub_col1, max_sub_col2, max_sub_col3, max_sub_col4]
    max_option_lists = [max_options_col1, max_options_col2, max_options_col3, max_options_col4]
    
    for i in range(4):
        col_options = max_option_lists[i]
        radio_key = f"radio_y_max_gain_col{i+1}"
        default_index = get_radio_index(col_options, "selected_max_gain_value")
        
        with max_cols[i]:
            st.radio(
                f"最大目盛 (列{i+1})",
                options=col_options,
                index=default_index if default_index is not None else 0,
                key=radio_key,
                on_change=lambda key=radio_key: update_gain_value(key, "selected_max_gain_value"),
                label_visibility="collapsed"
            )

    # 最終的な最大目盛の値
    selected_max_text = st.session_state["selected_max_gain_value"]
    y_max_gain = float(selected_max_text.replace('+', '').replace('', ''))

# --- 目盛りの範囲を設定 ---
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

if not selected_plot_tickers:
    st.info("グラフに表示する銘柄を上記マルチセレクトで選択してください。")
elif data_raw_5y.empty or daily_data_for_table.empty:
    st.info("データがロードされていないため、グラフを表示できません。")
else:
    # グラフ表示対象のティッカーリストを準備
    plot_tickers = selected_plot_tickers[:]
    if '^N225' in data_raw_5y.columns and '^N225' not in plot_tickers:
        plot_tickers.append('^N225') 
        
    FIXED_PLOT_PERIODS = {
        # 日次データ (daily_data_for_table: 3ヶ月分)
        "1日": {"period": "1日", "y_range": CHART_Y_RANGE["1日"], "data_source": "daily"}, 
        "5日": {"period": "5日", "y_range": CHART_Y_RANGE["5日"], "data_source": "daily"},
        "1ヶ月": {"period": "1ヶ月", "y_range": CHART_Y_RANGE["1ヶ月"], "data_source": "daily"},
        # 週次データ (data_raw_5y: 5年分)
        "3ヶ月": {"period": "3ヶ月", "y_range": CHART_Y_RANGE["3ヶ月"], "data_source": "weekly"}, 
        "6ヶ月": {"period": "6ヶ月", "y_range": CHART_Y_RANGE["6ヶ月"], "data_source": "weekly"}, 
        "1年": {"period": "1年", "y_range": CHART_Y_RANGE["1年"], "data_source": "weekly"},
        "3年": {"period": "3年", "y_range": CHART_Y_RANGE["3年"], "data_source": "weekly"},
        "5年": {"period": "5年", "y_range": CHART_Y_RANGE["5年"], "data_source": "weekly"},
    }
    
    tabs = st.tabs(list(FIXED_PLOT_PERIODS.keys()))
    
    # Y軸の自動スケール設定
    auto_scale = False

    for i, (period_label, config) in enumerate(FIXED_PLOT_PERIODS.items()):
        with tabs[i]:
            plot_data_raw = pd.DataFrame()
            if config["data_source"] == "daily":
                # 3ヶ月の日次データから期間を抽出
                if period_label == "1日":
                    plot_data_raw = daily_data_for_table.tail(2) # 2営業日 = 1日騰落率
                elif period_label == "5日":
                    plot_data_raw = daily_data_for_table.tail(6) # 6営業日 = 5日騰落率
                else: # 1ヶ月 (3ヶ月データ全体を使い、最初の価格を基準にする)
                    plot_data_raw = daily_data_for_table
            else: # weeklyデータ (週次データから期間を抽出)
                plot_data_raw = filter_data_by_period(data_raw_5y, config["period"])

            plot_tickers_in_data = [t for t in plot_tickers if t in plot_data_raw.columns] 	 	 
            
            if plot_tickers_in_data and not plot_data_raw.empty and plot_data_raw.shape[0] >= 2:
                plot_data_raw = plot_data_raw[plot_tickers_in_data].copy()
                
                # 期間の最初の有効な価格を取得
                # iloc[0]がNaNでないティッカーのみを対象
                first_valid_price = plot_data_raw.iloc[0].copy()
                valid_first_prices = first_valid_price[first_valid_price.index.isin(plot_data_raw.columns)].dropna()
                
                if not valid_first_prices.empty:
                    # 最初の価格で正規化
                    plot_data_raw = plot_data_raw[valid_first_prices.index].copy()
                    extracted_normalized = plot_data_raw / valid_first_prices 
                    
                    y_min, y_max = config["y_range"] 	 	 
                    
                    # グラフ描画関数の呼び出し
                    create_and_display_charts(
                        extracted_normalized, 
                        period_label, 
                        y_min, 
                        y_max,
                        auto_scale=auto_scale
                    )
                else:
                    st.info(f"選択された銘柄について「{period_label}」の有効なデータがありませんでした。")
            else:
                st.info(f"選択された銘柄について「{period_label}」の有効なデータがありませんでした。")


# --------------------------------------------------------------------------------------
# --- 棒グラフの配置 (日次騰落率)
# --------------------------------------------------------------------------------------
# 日ごとの騰落率データを計算（直近1ヶ月分を抽出）
df_daily_returns = calculate_daily_returns_df(daily_data_for_table)

if not df_daily_returns.empty and FILTERED_STOCKS:
    # フィルタリングされた銘柄のみを対象とする
    current_tickers = list(FILTERED_STOCKS.keys())
    # データをフィルタリングされた銘柄の列のみに絞る
    plot_daily_returns = df_daily_returns[[t for t in current_tickers if t in df_daily_returns.columns]].copy()
    
    # 日経平均（^N225）を除外
    plot_daily_returns_filtered = plot_daily_returns.drop(columns=['^N225'], errors='ignore')

    if not plot_daily_returns_filtered.empty:
        st.markdown("---") # 折れ線グラフのセクションと区切る
        st.markdown(f"## 📊 Daily Gain Chart")
        
        # Y軸のMin/Max設定 (元のプロンプトの例の固定値 ±5.0% を採用)
        daily_y_min = -5.0 
        daily_y_max = 5.0  
        
        # 日経平均を除外した、フィルタリングされた銘柄のリスト
        filtered_stocks_only = {k: v for k, v in FILTERED_STOCKS.items() if k != '^N225'}
        
        create_and_display_bar_charts(
            plot_daily_returns_filtered, 
            filtered_stocks_only, 
            "1ヶ月", 
            daily_y_min, 
            daily_y_max
        )
    else:
        st.info("日ごとの騰落率棒グラフを表示するためのデータが不足しています。")
elif daily_data_for_table.empty:
    pass # データロード失敗のメッセージは上部で表示済み
else:
    pass # 銘柄が選択されていない場合のメッセージは上部で表示済み
# --------------------------------------------------------------------------------------