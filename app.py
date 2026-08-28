import os
import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import requests
from dotenv import load_dotenv

# ==========================================
# 0. 환경 변수(.env / st.secrets) 로드
# ==========================================
load_dotenv()
FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY", "").strip()
if not FINNHUB_API_KEY and "FINNHUB_API_KEY" in st.secrets:
    FINNHUB_API_KEY = str(st.secrets["FINNHUB_API_KEY"]).strip()

# ==========================================
# 1. 페이지 설정 및 커스텀 스타일
# ==========================================
st.set_page_config(
    page_title="글로벌 주식 실시간 분석 대시보드",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 커스텀 CSS
st.markdown("""
<style>
    /* 상단 실시간 티커 바 컨테이너 */
    .realtime-bar-title {
        font-size: 1.1rem;
        font-weight: 700;
        margin-bottom: 8px;
        color: #38bdf8;
        display: flex;
        align-items: center;
        gap: 6px;
    }
    .live-badge {
        background-color: #ef4444;
        color: white;
        font-size: 0.65rem;
        font-weight: 700;
        padding: 2px 6px;
        border-radius: 4px;
        animation: pulse 1.5s infinite;
    }
    @keyframes pulse {
        0% { opacity: 1; }
        50% { opacity: 0.5; }
        100% { opacity: 1; }
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. Finnhub 실시간 시세 조회 함수
# ==========================================
@st.cache_data(ttl=30)  # 30초 캐시
def get_finnhub_quote(symbol: str, api_key: str):
    """Finnhub Quote API를 호출하여 미국 종목 실시간 시세를 반환"""
    if not api_key:
        return None
    try:
        url = f"https://finnhub.io/api/v1/quote?symbol={symbol}&token={api_key}"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            # 데이터 검증 (c가 0이면 잘못된 티커이거나 장외 미거래)
            if data.get("c", 0) != 0:
                return data
    except Exception as e:
        print(f"Finnhub API Error ({symbol}): {e}")
    return None

# ==========================================
# 3. 화면 상단: 미국 주요 종목 실시간 시세 배너
# ==========================================
LIVE_WATCHLIST = ["AAPL", "NVDA", "TSLA", "MSFT", "AMZN"]

col_header1, col_header2 = st.columns([4, 1])
with col_header1:
    st.markdown(
        '<div class="realtime-bar-title">⚡ 미국 주요 종목 실시간 시세 (Finnhub API 연동) <span class="live-badge">LIVE</span></div>',
        unsafe_allow_html=True
    )
with col_header2:
    if st.button("🔄 실시간 시세 갱신", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

if FINNHUB_API_KEY:
    live_cols = st.columns(len(LIVE_WATCHLIST))
    for idx, sym in enumerate(LIVE_WATCHLIST):
        q = get_finnhub_quote(sym, FINNHUB_API_KEY)
        with live_cols[idx]:
            if q:
                curr_p = q.get("c", 0)   # 현재가
                chg = q.get("d", 0)      # 변동액
                chg_pct = q.get("dp", 0) # 변동률(%)
                st.metric(
                    label=f"🇺🇸 {sym}",
                    value=f"${curr_p:,.2f}",
                    delta=f"{chg:+,.2f} ({chg_pct:+.2f}%)"
                )
            else:
                st.metric(label=f"🇺🇸 {sym}", value="조회 불가", delta=None)
else:
    st.warning("⚠️ `.env` 파일에 `FINNHUB_API_KEY`가 설정되지 않았습니다. 실시간 시세를 확인하려면 키를 입력해주세요.")

st.markdown("---")

# ==========================================
# 4. 사이드바 구성
# ==========================================
st.sidebar.title("📊 설정 및 검색")

# 대표 종목 프리셋
PRESET_STOCKS = {
    "직접 입력": "",
    "삼성전자 (005930.KS)": "005930.KS",
    "SK하이닉스 (000660.KS)": "000660.KS",
    "현대차 (005380.KS)": "005380.KS",
    "NAVER (035420.KS)": "035420.KS",
    "카카오 (035720.KS)": "035720.KS",
    "Apple (AAPL)": "AAPL",
    "NVIDIA (NVDA)": "NVDA",
    "Tesla (TSLA)": "TSLA",
    "Microsoft (MSFT)": "MSFT",
    "Alphabet / Google (GOOGL)": "GOOGL",
}

selected_preset = st.sidebar.selectbox("🌟 인기 종목 바로가기", list(PRESET_STOCKS.keys()))

if selected_preset == "직접 입력":
    default_ticker = "AAPL"
else:
    default_ticker = PRESET_STOCKS[selected_preset]

ticker_input = st.sidebar.text_input(
    "티커 심볼 입력",
    value=default_ticker,
    help="미국: AAPL, TSLA 등 / 한국(코스피): 005930.KS, 한국(코스닥): 035900.KQ"
).strip().upper()

# 기간 선택
period_map = {
    "1개월": "1mo",
    "6개월": "6mo",
    "1년": "1y",
    "5년": "5y"
}
selected_period_label = st.sidebar.radio("📅 조회 기간", list(period_map.keys()), index=2)
period_code = period_map[selected_period_label]

st.sidebar.markdown("---")
st.sidebar.info(
    "💡 **티커 입력 팁**\n"
    "- **미국 주식**: `AAPL`, `TSLA`, `NVDA`, `SPY`\n"
    "- **코스피**: 뒤에 `.KS` (예: `005930.KS`)\n"
    "- **코스닥**: 뒤에 `.KQ` (예: `091990.KQ`)\n"
    "- **상단 카드**: Finnhub 실시간 체결 시세 적용"
)

# ==========================================
# 5. 주가 데이터 로딩 및 지표 계산
# ==========================================
@st.cache_data(ttl=300)
def load_stock_data(ticker: str, period: str):
    stock = yf.Ticker(ticker)
    df = stock.history(period=period)
    info = stock.info if hasattr(stock, "info") else {}
    return df, info

if not ticker_input:
    st.warning("사이드바에서 티커 심볼을 입력하거나 선택해 주세요.")
    st.stop()

with st.spinner(f"'{ticker_input}' 주가 데이터를 불러오는 중입니다..."):
    try:
        df, info = load_stock_data(ticker_input, period_code)
    except Exception as e:
        st.error(f"데이터를 불러오는 중 오류가 발생했습니다: {e}")
        st.stop()

if df.empty:
    st.error(f"'{ticker_input}'에 대한 주가 데이터를 찾을 수 없습니다. 티커 심볼을 확인해 주세요.")
    st.stop()

# 이동평균선 계산
df["MA20"] = df["Close"].rolling(window=20).mean()
df["MA60"] = df["Close"].rolling(window=60).mean()

# 회사 이름 및 통화 단위
company_name = info.get("shortName") or info.get("longName") or ticker_input
currency = info.get("currency", "USD")
currency_symbol = "₩" if currency in ["KRW", "KRW "] else ("$" if currency == "USD" else f"{currency} ")

# 미국 주식이면 Finnhub 실시간 쿼트 추가 확인
is_us_stock = not (ticker_input.endswith(".KS") or ticker_input.endswith(".KQ"))
live_quote_data = None
if is_us_stock and FINNHUB_API_KEY:
    live_quote_data = get_finnhub_quote(ticker_input, FINNHUB_API_KEY)

# ==========================================
# 6. 헤더 및 요약 지표 영역
# ==========================================
col_title, col_time = st.columns([3, 1])
with col_title:
    st.title(f"{company_name} ({ticker_input})")
    stock_type_str = "미국 주식 (실시간 Finnhub 연동 가능)" if is_us_stock else "한국 주식 (KRX)"
    st.caption(f"구분: {stock_type_str} | 통화: {currency} | 차트 기간: {selected_period_label}")
with col_time:
    last_date = df.index[-1].strftime("%Y-%m-%d")
    st.markdown(f"<div style='text-align:right; color:#94a3b8;'>최근 차트 기준일<br><b>{last_date}</b></div>", unsafe_allow_html=True)

# 지표 계산
latest_close = df["Close"].iloc[-1]
start_close = df["Close"].iloc[0]

total_return = ((latest_close - start_close) / start_close) * 100
total_diff = latest_close - start_close

highest_price = df["High"].max()
lowest_price = df["Low"].min()

prev_close = df["Close"].iloc[-2] if len(df) > 1 else start_close
daily_diff = latest_close - prev_close
daily_pct = (daily_diff / prev_close) * 100

st.markdown("### 📌 핵심 요약 지표")
c1, c2, c3, c4 = st.columns(4)

def format_price(val):
    if currency == "KRW":
        return f"{currency_symbol}{val:,.0f}"
    return f"{currency_symbol}{val:,.2f}"

with c1:
    if live_quote_data:
        curr_p = live_quote_data.get("c", latest_close)
        chg = live_quote_data.get("d", daily_diff)
        chg_p = live_quote_data.get("dp", daily_pct)
        st.metric(
            label="실시간 현재가 (Live)",
            value=f"${curr_p:,.2f}",
            delta=f"{chg:+,.2f} ({chg_p:+.2f}%)"
        )
    else:
        st.metric(
            label="최근 종가",
            value=format_price(latest_close),
            delta=f"{daily_diff:+,.2f} ({daily_pct:+.2f}%)" if currency != "KRW" else f"{daily_diff:+,.0f} ({daily_pct:+.2f}%)"
        )

with c2:
    st.metric(
        label=f"{selected_period_label} 총 수익률",
        value=f"{total_return:+.2f}%",
        delta=f"{format_price(total_diff)} 변동"
    )

with c3:
    st.metric(
        label=f"{selected_period_label} 최고가",
        value=format_price(highest_price)
    )

with c4:
    st.metric(
        label=f"{selected_period_label} 최저가",
        value=format_price(lowest_price)
    )

st.markdown("<br>", unsafe_allow_html=True)

# ==========================================
# 7. 메인 차트: 인터랙티브 캔들스틱 + 이평선 + 거래량
# ==========================================
st.markdown("### 📈 인터랙티브 캔들스틱 차트")

fig = make_subplots(
    rows=2, cols=1,
    shared_xaxes=True,
    vertical_spacing=0.04,
    row_heights=[0.75, 0.25],
    subplot_titles=(f"{ticker_input} 주가 및 이동평균선", "거래량 (Volume)")
)

# 1) 캔들스틱 차트
fig.add_trace(
    go.Candlestick(
        x=df.index,
        open=df["Open"],
        high=df["High"],
        low=df["Low"],
        close=df["Close"],
        name="주가",
        increasing_line_color="#ef4444",  # 상승: 빨강
        decreasing_line_color="#3b82f6"   # 하락: 파랑
    ),
    row=1, col=1
)

# 2) 20일 이동평균선
fig.add_trace(
    go.Scatter(
        x=df.index,
        y=df["MA20"],
        line=dict(color="#f59e0b", width=1.5),
        name="20일 이평선"
    ),
    row=1, col=1
)

# 3) 60일 이동평균선
fig.add_trace(
    go.Scatter(
        x=df.index,
        y=df["MA60"],
        line=dict(color="#10b981", width=1.5),
        name="60일 이평선"
    ),
    row=1, col=1
)

# 4) 거래량 바 차트
colors = ['#ef4444' if row['Close'] >= row['Open'] else '#3b82f6' for _, row in df.iterrows()]
fig.add_trace(
    go.Bar(
        x=df.index,
        y=df["Volume"],
        name="거래량",
        marker_color=colors,
        opacity=0.7
    ),
    row=2, col=1
)

# 차트 레이아웃 스타일
fig.update_layout(
    height=600,
    xaxis_rangeslider_visible=False,
    template="plotly_dark",
    margin=dict(l=20, r=20, t=40, b=20),
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="right",
        x=1
    ),
    hovermode="x unified"
)

fig.update_yaxes(title_text=f"가격 ({currency})", row=1, col=1)
fig.update_yaxes(title_text="거래량", row=2, col=1)

st.plotly_chart(fig, use_container_width=True)

# ==========================================
# 8. 상세 데이터 및 CSV 다운로드
# ==========================================
with st.expander("📋 상세 주가 데이터 및 CSV 다운로드"):
    display_df = df[["Open", "High", "Low", "Close", "Volume", "MA20", "MA60"]].sort_index(ascending=False)
    st.dataframe(display_df.style.format({
        "Open": "{:,.2f}",
        "High": "{:,.2f}",
        "Low": "{:,.2f}",
        "Close": "{:,.2f}",
        "Volume": "{:,.0f}",
        "MA20": "{:,.2f}",
        "MA60": "{:,.2f}",
    }), use_container_width=True)
    
    csv_data = display_df.to_csv().encode('utf-8')
    st.download_button(
        label="📥 CSV 파일로 다운로드",
        data=csv_data,
        file_name=f"{ticker_input}_{selected_period_label}_stock_data.csv",
        mime="text/csv",
    )
