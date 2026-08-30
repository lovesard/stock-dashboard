import os
import streamlit as st
import streamlit.components.v1 as components
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
import requests
from dotenv import load_dotenv

# ==========================================
# 0. 환경 변수 (.env / st.secrets) 로드
# ==========================================
load_dotenv()
FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY", "").strip()
if not FINNHUB_API_KEY and "FINNHUB_API_KEY" in st.secrets:
    FINNHUB_API_KEY = str(st.secrets["FINNHUB_API_KEY"]).strip()

# ==========================================
# 1. 페이지 설정 및 커스텀 스타일
# ==========================================
st.set_page_config(
    page_title="글로벌 주식 올인원 분석 대시보드",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 커스텀 CSS
st.markdown("""
<style>
    /* 상단 실시간 티커 바 */
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
    .metric-card {
        background: #1e293b;
        border-radius: 10px;
        padding: 14px;
        border: 1px solid #334155;
    }
    .metric-title {
        font-size: 0.85rem;
        color: #94a3b8;
        margin-bottom: 4px;
    }
    .metric-value {
        font-size: 1.25rem;
        font-weight: 700;
        color: #f8fafc;
    }
    .signal-badge-bull {
        display: inline-block;
        background: #15803d;
        color: #f0fdf4;
        padding: 3px 8px;
        border-radius: 6px;
        font-size: 0.8rem;
        font-weight: bold;
    }
    .signal-badge-bear {
        display: inline-block;
        background: #b91c1c;
        color: #fef2f2;
        padding: 3px 8px;
        border-radius: 6px;
        font-size: 0.8rem;
        font-weight: bold;
    }
    .signal-badge-neutral {
        display: inline-block;
        background: #475569;
        color: #f1f5f9;
        padding: 3px 8px;
        border-radius: 6px;
        font-size: 0.8rem;
        font-weight: bold;
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
        '<div class="realtime-bar-title">⚡ 미국 대표 종목 실시간 시세 (Finnhub API) <span class="live-badge">LIVE</span></div>',
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
                curr_p = q.get("c", 0)
                chg = q.get("d", 0)
                chg_pct = q.get("dp", 0)
                st.metric(
                    label=f"🇺🇸 {sym}",
                    value=f"${curr_p:,.2f}",
                    delta=f"{chg:+,.2f} ({chg_pct:+.2f}%)"
                )
            else:
                st.metric(label=f"🇺🇸 {sym}", value="조회 대기", delta=None)
else:
    st.warning("⚠️ `.env` 또는 Streamlit Secrets에 `FINNHUB_API_KEY`를 등록하면 미국 실시간 시세가 활성화됩니다.")

st.markdown("---")

# ==========================================
# 4. 스마트 종목 검색 헬퍼 및 한글 사전
# ==========================================
KOREAN_STOCK_ALIAS = {
    # 미국 주요 종목
    "템퍼스": ("TEM", "Tempus AI"),
    "템퍼스AI": ("TEM", "Tempus AI"),
    "템퍼스에이아이": ("TEM", "Tempus AI"),
    "팔란티어": ("PLTR", "Palantir Technologies"),
    "아이온큐": ("IONQ", "IonQ Inc"),
    "사운드하운드": ("SOUN", "SoundHound AI"),
    "엔비디아": ("NVDA", "NVIDIA Corporation"),
    "테슬라": ("TSLA", "Tesla, Inc."),
    "애플": ("AAPL", "Apple Inc."),
    "마이크로소프트": ("MSFT", "Microsoft Corporation"),
    "마소": ("MSFT", "Microsoft Corporation"),
    "구글": ("GOOGL", "Alphabet Inc."),
    "알파벳": ("GOOGL", "Alphabet Inc."),
    "아마존": ("AMZN", "Amazon.com, Inc."),
    "메타": ("META", "Meta Platforms, Inc."),
    "페이스북": ("META", "Meta Platforms, Inc."),
    "넷플릭스": ("NFLX", "Netflix, Inc."),
    "브로드컴": ("AVGO", "Broadcom Inc."),
    "슈퍼마이크로": ("SMCI", "Super Micro Computer"),
    "코인베이스": ("COIN", "Coinbase Global"),
    "AMD": ("AMD", "Advanced Micro Devices"),
    "인텔": ("INTC", "Intel Corporation"),
    "TSMC": ("TSM", "Taiwan Semiconductor"),
    "버크셔": ("BRK-B", "Berkshire Hathaway"),
    "코카콜라": ("KO", "Coca-Cola"),
    "비트코인": ("BTC-USD", "Bitcoin USD"),
    # 한국 주요 종목
    "삼성전자": ("005930.KS", "삼성전자"),
    "삼전": ("005930.KS", "삼성전자"),
    "삼성전자우": ("005935.KS", "삼성전자(우)"),
    "SK하이닉스": ("000660.KS", "SK하이닉스"),
    "하이닉스": ("000660.KS", "SK하이닉스"),
    "현대차": ("005380.KS", "현대자동차"),
    "기아": ("000270.KS", "기아"),
    "NAVER": ("035420.KS", "NAVER"),
    "네이버": ("035420.KS", "NAVER"),
    "카카오": ("035720.KS", "카카오"),
    "셀트리온": ("068270.KS", "셀트리온"),
    "알테오젠": ("196170.KQ", "알테오젠"),
    "에코프로": ("086520.KQ", "에코프로"),
    "에코프로비엠": ("247540.KQ", "에코프로비엠"),
    "LG에너지솔루션": ("373220.KS", "LG에너지솔루션"),
    "엔솔": ("373220.KS", "LG에너지솔루션"),
    "POSCO홀딩스": ("005490.KS", "POSCO홀딩스"),
    "포스코": ("005490.KS", "POSCO홀딩스"),
    "크래프톤": ("259960.KS", "크래프톤"),
    "하이브": ("352820.KS", "하이브"),
}

@st.cache_data(ttl=3600)
def search_yahoo_finance(query: str):
    """야후 파이낸스 검색 API로 티커 및 회사명 검색"""
    if not query or len(query.strip()) < 1:
        return []
    url = "https://query2.finance.yahoo.com/v1/finance/search"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    params = {"q": query, "quotesCount": 6, "newsCount": 0}
    try:
        res = requests.get(url, headers=headers, params=params, timeout=4)
        if res.status_code == 200:
            quotes = res.json().get("quotes", [])
            results = []
            for q in quotes:
                symbol = q.get("symbol")
                name = q.get("shortname") or q.get("longname") or symbol
                exch = q.get("exchange", "")
                if symbol:
                    results.append((symbol, f"{symbol} - {name} ({exch})"))
            return results
    except Exception as e:
        print(f"Search API Error: {e}")
    return []

# ==========================================
# 5. 사이드바: 큐레이션 워치리스트 & 스마트 검색
# ==========================================
st.sidebar.title("🔍 종목 탐색 & 큐레이션")

# 1) 테마별 워치리스트 카테고리
THEME_WATCHLISTS = {
    "🌟 빅테크 매그니피센트 7 (M7)": {
        "Apple (AAPL)": "AAPL",
        "NVIDIA (NVDA)": "NVDA",
        "Microsoft (MSFT)": "MSFT",
        "Alphabet/Google (GOOGL)": "GOOGL",
        "Amazon (AMZN)": "AMZN",
        "Meta Platforms (META)": "META",
        "Tesla (TSLA)": "TSLA"
    },
    "🤖 AI 혁신 & 차세대 기술주": {
        "Palantir (PLTR)": "PLTR",
        "Tempus AI (TEM)": "TEM",
        "Broadcom (AVGO)": "AVGO",
        "Super Micro (SMCI)": "SMCI",
        "IonQ (IONQ)": "IONQ",
        "SoundHound AI (SOUN)": "SOUN",
        "TSMC (TSM)": "TSM"
    },
    "🇰🇷 국내 대표 대장주 (KOSPI/KOSDAQ)": {
        "삼성전자 (005930.KS)": "005930.KS",
        "SK하이닉스 (000660.KS)": "000660.KS",
        "현대차 (005380.KS)": "005380.KS",
        "알테오젠 (196170.KQ)": "196170.KQ",
        "NAVER (035420.KS)": "035420.KS",
        "에코프로비엠 (247540.KQ)": "247540.KQ",
        "LG에너지솔루션 (373220.KS)": "373220.KS"
    },
    "💰 배당 / 가치 / 가상자산": {
        "버크셔 해서웨이 (BRK-B)": "BRK-B",
        "코카콜라 (KO)": "KO",
        "비트코인 (BTC-USD)": "BTC-USD",
        "코인베이스 (COIN)": "COIN"
    }
}

selected_theme = st.sidebar.selectbox("📂 테마별 큐레이션 워치리스트", list(THEME_WATCHLISTS.keys()))
theme_stocks = THEME_WATCHLISTS[selected_theme]
selected_theme_stock = st.sidebar.selectbox("📌 큐레이션 종목 빠른 선택", list(theme_stocks.keys()))
preset_ticker = theme_stocks[selected_theme_stock]

st.sidebar.markdown("---")

# 2) 스마트 직접 검색
search_kw = st.sidebar.text_input(
    "🔎 직접 검색 (한글명 / 영문 / 티커)",
    value="",
    placeholder="예: 팔란티어, 삼전, AAPL, 000660",
    help="한글 기업명이나 티커를 입력하면 즉시 매핑됩니다."
).strip()

final_ticker = preset_ticker

# 검색어 자동 매칭
found_options = {}
kw_clean = search_kw.replace(" ", "").upper()
if kw_clean:
    for alias, (sym, name) in KOREAN_STOCK_ALIAS.items():
        if kw_clean in alias.upper() or alias.upper() in kw_clean:
            found_options[f"🇰🇷 {alias} ({sym}) - {name}"] = sym

if search_kw:
    api_results = search_yahoo_finance(search_kw)
    for sym, label in api_results:
        found_options[label] = sym

if found_options:
    selected_item = st.sidebar.selectbox("✨ 검색 결과 선택", list(found_options.keys()))
    final_ticker = found_options[selected_item]
elif search_kw:
    final_ticker = search_kw.upper()

ticker_input = final_ticker.strip().upper()
st.sidebar.caption(f"선택된 티커: **`{ticker_input}`**")

# 기간 선택
period_map = {
    "1개월": "1mo",
    "3개월": "3mo",
    "6개월": "6mo",
    "1년": "1y",
    "2년": "2y",
    "5년": "5y"
}
selected_period_label = st.sidebar.radio("📅 백엔드 데이터 분석 기간", list(period_map.keys()), index=3)
period_code = period_map[selected_period_label]

st.sidebar.markdown("---")
st.sidebar.info("""
💡 **대시보드 200% 활용 가이드**
- **트레이딩뷰 탭**: 완벽한 전문 차트, 모든 지표 및 자유 작도(Alt+T, Alt+H)를 영구 보존 사용
- **퀀트 & 펀더멘털 탭**: 파이썬이 계산한 재무 비율, 피보나치 자동 매물대, 20일선 백테스팅 결과 확인
""")

# ==========================================
# 6. 주가 데이터 및 재무 정보 로드
# ==========================================
@st.cache_data(ttl=300)
def load_stock_data(ticker: str, period: str):
    stock = yf.Ticker(ticker)
    df = stock.history(period=period)
    info = stock.info if hasattr(stock, "info") else {}
    return df, info

with st.spinner(f"'{ticker_input}' 데이터 분석 중..."):
    try:
        df, info = load_stock_data(ticker_input, period_code)
    except Exception as e:
        st.error(f"데이터 로드 오류: {e}")
        st.stop()

if df.empty:
    st.error(f"'{ticker_input}' 주가 데이터를 찾을 수 없습니다. 티커를 확인해주세요.")
    st.stop()

# 보조지표 계산 (이동평균선 & RSI)
df["MA5"] = df["Close"].rolling(window=5).mean()
df["MA20"] = df["Close"].rolling(window=20).mean()
df["MA60"] = df["Close"].rolling(window=60).mean()
df["MA120"] = df["Close"].rolling(window=120).mean()

# RSI(14) 계산
delta = df["Close"].diff()
gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
rs = gain / loss
df["RSI"] = 100 - (100 / (1 + rs))

# 회사 정보 및 통화
company_name = info.get("shortName") or info.get("longName") or ticker_input
currency = info.get("currency", "USD")
currency_symbol = "₩" if currency in ["KRW", "KRW "] else ("$" if currency == "USD" else f"{currency} ")

def format_price(val):
    if pd.isna(val) or val is None:
        return "-"
    if currency == "KRW":
        return f"{currency_symbol}{val:,.0f}"
    return f"{currency_symbol}{val:,.2f}"

def format_num(val):
    if pd.isna(val) or val is None:
        return "-"
    if abs(val) >= 1e12:
        return f"{val/1e12:.2f}조"
    elif abs(val) >= 1e8:
        return f"{val/1e8:.2f}억"
    return f"{val:,.2f}"

is_us_stock = not (ticker_input.endswith(".KS") or ticker_input.endswith(".KQ"))
live_quote_data = None
if is_us_stock and FINNHUB_API_KEY:
    live_quote_data = get_finnhub_quote(ticker_input, FINNHUB_API_KEY)

# ==========================================
# 7. 상단 헤더 및 핵심 요약 지표
# ==========================================
col_title, col_time = st.columns([3, 1])
with col_title:
    st.title(f"{company_name} ({ticker_input})")
    stock_type_str = "미국 주식 (Finnhub 실시간 연동)" if is_us_stock else "한국 주식 (KRX)"
    st.caption(f"구분: {stock_type_str} | 통화: {currency} | 기준 분석 기간: {selected_period_label}")
with col_time:
    last_date = df.index[-1].strftime("%Y-%m-%d")
    st.markdown(f"<div style='text-align:right; color:#94a3b8;'>최근 종가 기준일<br><b>{last_date}</b></div>", unsafe_allow_html=True)

latest_close = df["Close"].iloc[-1]
start_close = df["Close"].iloc[0]
total_return = ((latest_close - start_close) / start_close) * 100
highest_price = df["High"].max()
lowest_price = df["Low"].min()

prev_close = df["Close"].iloc[-2] if len(df) > 1 else start_close
daily_diff = latest_close - prev_close
daily_pct = (daily_diff / prev_close) * 100

st.markdown("### 📊 핵심 시세 요약")
c1, c2, c3, c4 = st.columns(4)

with c1:
    if live_quote_data:
        curr_p = live_quote_data.get("c", latest_close)
        chg = live_quote_data.get("d", daily_diff)
        chg_p = live_quote_data.get("dp", daily_pct)
        st.metric("현재가 (실시간)", format_price(curr_p), f"{chg:+,.2f} ({chg_p:+.2f}%)")
    else:
        st.metric("최근 종가", format_price(latest_close), f"{daily_diff:+,.2f} ({daily_pct:+.2f}%)")

with c2:
    st.metric(f"{selected_period_label} 기간 수익률", f"{total_return:+.2f}%", f"{latest_close - start_close:+,.2f}")

with c3:
    st.metric(f"{selected_period_label} 최고가 (High)", format_price(highest_price))

with c4:
    st.metric(f"{selected_period_label} 최저가 (Low)", format_price(lowest_price))

st.markdown("---")

# ==========================================
# 8. 메인 분석 탭 구성 (역할 명확 분리)
# ==========================================
tab_tv, tab_quant, tab_backtest = st.tabs([
    "🌟 트레이딩뷰 프로 차트 (TradingView Studio)",
    "📑 펀더멘털 & 퀀트 매물대 분석",
    "📈 이동평균선 돌파 백테스팅 시뮬레이션"
])

# ----------------------------------------------------
# 탭 1: 트레이딩뷰 프로 차트 (차트 및 자유 작도 완벽 제공)
# ----------------------------------------------------
def get_tradingview_symbol(ticker: str):
    t = ticker.upper().strip()
    if t.endswith(".KS"):
        return f"KRX:{t.replace('.KS', '')}"
    elif t.endswith(".KQ"):
        return f"KOSDAQ:{t.replace('.KQ', '')}"
    elif t == "BTC-USD":
        return "BINANCE:BTCUSDT"
    elif ":" in t:
        return t
    else:
        return t

tv_symbol = get_tradingview_symbol(ticker_input)

with tab_tv:
    col_tva, col_tvb = st.columns([3, 1])
    with col_tva:
        st.caption("💡 **트레이딩뷰 작도 팁**: 좌측 툴바에서 **추세선(Alt+T)**, **수평선(Alt+H)**, **피보나치**, 박스 등을 자유롭게 작도하면 브라우저에 영구 자동 저장됩니다.")
    with col_tvb:
        st.caption("⚡ 상단 지표 메뉴에서 볼린저밴드, MACD 등 100+개 지표를 추가할 수 있습니다.")

    tv_widget_html = f"""
    <!-- TradingView Widget BEGIN -->
    <div class="tradingview-widget-container" style="height:670px;width:100%">
      <div id="tradingview_pro_chart" style="height:calc(100% - 32px);width:100%"></div>
      <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
      <script type="text/javascript">
      new TradingView.widget(
      {{
        "autosize": true,
        "symbol": "{tv_symbol}",
        "interval": "D",
        "timezone": "Asia/Seoul",
        "theme": "dark",
        "style": "1",
        "locale": "kr",
        "toolbar_bg": "#1e293b",
        "enable_publishing": false,
        "hide_side_toolbar": false,
        "allow_symbol_change": true,
        "save_image": true,
        "details": true,
        "hotlist": true,
        "calendar": true,
        "studies": [
          "MASimple@tv-basicstudies",
          "MAExp@tv-basicstudies",
          "RSI@tv-basicstudies"
        ],
        "container_id": "tradingview_pro_chart"
      }}
      );
      </script>
    </div>
    <!-- TradingView Widget END -->
    """
    components.html(tv_widget_html, height=680)

# ----------------------------------------------------
# 탭 2: 펀더멘털 & 퀀트 알고리즘 매물대 분석
# ----------------------------------------------------
with tab_quant:
    st.subheader("🏢 기업 재무 펀더멘털 & 밸류에이션")
    
    mcap = info.get("marketCap")
    pe_trailing = info.get("trailingPE")
    pe_forward = info.get("forwardPE")
    pbr = info.get("priceToBook")
    eps = info.get("trailingEps")
    div_yield = info.get("dividendYield")
    target_price = info.get("targetMeanPrice")
    rec_key = info.get("recommendationKey", "-").upper()
    beta = info.get("beta")

    q_col1, q_col2, q_col3, q_col4 = st.columns(4)
    with q_col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">시가총액 (Market Cap)</div>
            <div class="metric-value">{format_num(mcap) if mcap else '-'}</div>
        </div>
        """, unsafe_allow_html=True)
    with q_col2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">PER (Trailing / Forward)</div>
            <div class="metric-value">{f'{pe_trailing:.1f}배' if pe_trailing else '-'} / {f'{pe_forward:.1f}배' if pe_forward else '-'}</div>
        </div>
        """, unsafe_allow_html=True)
    with q_col3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">PBR / EPS</div>
            <div class="metric-value">{f'{pbr:.2f}배' if pbr else '-'} / {format_price(eps) if eps else '-'}</div>
        </div>
        """, unsafe_allow_html=True)
    with q_col4:
        div_str = f"{div_yield*100:.2f}%" if div_yield else "0.00%"
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">배당수익률 / Beta</div>
            <div class="metric-value">{div_str} / {f'{beta:.2f}' if beta else '-'}</div>
        </div>
        """, unsafe_allow_html=True)

    # 애널리스트 투자의견 및 목표주가
    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
    col_rec1, col_rec2 = st.columns(2)
    with col_rec1:
        if target_price:
            upside = ((target_price - latest_close) / latest_close) * 100
            upside_color = "#10b981" if upside >= 0 else "#ef4444"
            st.info(f"🎯 **애널리스트 평균 목표주가**: **{format_price(target_price)}** (현재가 대비 예상 등락률: <span style='color:{upside_color}; font-weight:bold;'>{upside:+.2f}%</span>)", icon="🎯")
        else:
            st.info("🎯 **애널리스트 목표주가**: 제공 데이터 없음")
    with col_rec2:
        st.info(f"📢 **월가 컨센서스 투자의견**: **{rec_key}** (종합 분석 의견)", icon="📢")

    st.markdown("---")
    st.subheader("🎯 알고리즘 기반 자동 피보나치 매물대 & 지지/저항 레벨")
    st.caption("최근 고점과 저점을 기준으로 산출된 알고리즘 지지/저항선입니다. 수동 작도 없이 핵심 가격대를 한눈에 파악하세요.")

    diff_hl = highest_price - lowest_price
    fib_levels = {
        "최고점 (100.0%) - 강력 저항": highest_price,
        "피보나치 61.8% 되돌림": highest_price - 0.382 * diff_hl,
        "피보나치 50.0% 중심선": highest_price - 0.500 * diff_hl,
        "피보나치 38.2% 지지선": highest_price - 0.618 * diff_hl,
        "피보나치 23.6% 지지선": highest_price - 0.764 * diff_hl,
        "최저점 (0.0%) - 최종 지지": lowest_price,
    }

    fib_df = pd.DataFrame([
        {"주요 가격 레벨": k, "기준 가격": format_price(v), "현재가와의 거리": f"{((v - latest_close)/latest_close)*100:+.2f}%"}
        for k, v in fib_levels.items()
    ])
    st.table(fib_df)

    # 이동평균선 배열 & 추세 시그널
    st.subheader("⚡ 이동평균선 배열 & 모멘텀 진단")
    ma20_val = df["MA20"].iloc[-1]
    ma60_val = df["MA60"].iloc[-1]
    rsi_val = df["RSI"].iloc[-1] if "RSI" in df else 50.0

    sig_col1, sig_col2, sig_col3 = st.columns(3)
    with sig_col1:
        if latest_close >= ma20_val:
            st.markdown('**20일선 위치:** <span class="signal-badge-bull">20일선 위 (단기 상승세)</span>', unsafe_allow_html=True)
        else:
            st.markdown('**20일선 위치:** <span class="signal-badge-bear">20일선 아래 (단기 조정세)</span>', unsafe_allow_html=True)
        st.write(f"현재가: {format_price(latest_close)} / 20일선: {format_price(ma20_val)}")

    with sig_col2:
        if ma20_val >= ma60_val:
            st.markdown('**이평선 정배열 상태:** <span class="signal-badge-bull">정배열 (중기 상승 추세)</span>', unsafe_allow_html=True)
        else:
            st.markdown('**이평선 정배열 상태:** <span class="signal-badge-bear">역배열 (중기 하락 추세)</span>', unsafe_allow_html=True)
        st.write(f"20일선: {format_price(ma20_val)} / 60일선: {format_price(ma60_val)}")

    with sig_col3:
        if rsi_val >= 70:
            st.markdown(f'**RSI(14) 모멘텀:** <span class="signal-badge-bear">과매수 구간 ({rsi_val:.1f})</span>', unsafe_allow_html=True)
        elif rsi_val <= 30:
            st.markdown(f'**RSI(14) 모멘텀:** <span class="signal-badge-bull">과매도 구간 ({rsi_val:.1f})</span>', unsafe_allow_html=True)
        else:
            st.markdown(f'**RSI(14) 모멘텀:** <span class="signal-badge-neutral">중립 구간 ({rsi_val:.1f})</span>', unsafe_allow_html=True)
        st.write("30 이하: 반등 가능성 / 70 이상: 차익실현 경계")

# ----------------------------------------------------
# 탭 3: 이동평균선 돌파 퀀트 백테스팅 시뮬레이터
# ----------------------------------------------------
with tab_backtest:
    st.subheader("📈 20일 이동평균선 돌파 전략 백테스팅")
    st.caption("선택한 기간 동안 **'주가가 20일선을 상향 돌파 시 매수, 20일선을 하향 이탈 시 매도(현금화)'** 했을 때의 시뮬레이션 결과입니다.")

    bt_df = df.copy().dropna(subset=["MA20"])
    if len(bt_df) > 20:
        # 매매 시그널: 종가가 20일선보다 위에 있으면 보유(1), 아래면 현금(0)
        bt_df["Position"] = np.where(bt_df["Close"] > bt_df["MA20"], 1, 0)
        # 익일 수익률 적용 (Position은 전일 종가 기준 판단)
        bt_df["Market_Return"] = bt_df["Close"].pct_change()
        bt_df["Strategy_Return"] = bt_df["Market_Return"] * bt_df["Position"].shift(1)

        bt_df["Cum_Market"] = (1 + bt_df["Market_Return"]).cumprod() - 1
        bt_df["Cum_Strategy"] = (1 + bt_df["Strategy_Return"].fillna(0)).cumprod() - 1

        strat_final = bt_df["Cum_Strategy"].iloc[-1] * 100
        market_final = bt_df["Cum_Market"].iloc[-1] * 100

        b1, b2, b3 = st.columns(3)
        with b1:
            st.metric("전략 누적 수익률 (20일선 돌파)", f"{strat_final:+.2f}%")
        with b2:
            st.metric("단순 보유(Buy & Hold) 수익률", f"{market_final:+.2f}%")
        with b3:
            alpha = strat_final - market_final
            st.metric("전략 초과 수익 (Alpha)", f"{alpha:+.2f}%")

        # 비교 차트
        fig_bt = go.Figure()
        fig_bt.add_trace(go.Scatter(
            x=bt_df.index, y=bt_df["Cum_Strategy"] * 100,
            name="20일선 돌파 전략", line=dict(color="#10b981", width=2.5)
        ))
        fig_bt.add_trace(go.Scatter(
            x=bt_df.index, y=bt_df["Cum_Market"] * 100,
            name="단순 보유 (Buy & Hold)", line=dict(color="#94a3b8", width=1.5, dash="dash")
        ))
        fig_bt.update_layout(
            template="plotly_dark",
            height=450,
            margin=dict(l=20, r=20, t=30, b=20),
            yaxis_title="누적 수익률 (%)",
            hovermode="x unified"
        )
        st.plotly_chart(fig_bt, use_container_width=True)
    else:
        st.warning("백테스팅을 수행하기 위한 데이터가 충분하지 않습니다. 조회 기간을 6개월 이상으로 늘려주세요.")

# ==========================================
# 9. 상세 데이터 및 CSV 다운로드
# ==========================================
with st.expander("📋 상세 가격 데이터 및 CSV 다운로드"):
    display_df = df[["Open", "High", "Low", "Close", "Volume", "MA20", "MA60", "RSI"]].sort_index(ascending=False)
    st.dataframe(display_df.style.format({
        "Open": "{:,.2f}",
        "High": "{:,.2f}",
        "Low": "{:,.2f}",
        "Close": "{:,.2f}",
        "Volume": "{:,.0f}",
        "MA20": "{:,.2f}",
        "MA60": "{:,.2f}",
        "RSI": "{:,.1f}",
    }), use_container_width=True)
    
    csv_data = display_df.to_csv().encode('utf-8')
    st.download_button(
        label="📥 CSV 파일로 다운로드",
        data=csv_data,
        file_name=f"{ticker_input}_{selected_period_label}_stock_data.csv",
        mime="text/csv",
    )