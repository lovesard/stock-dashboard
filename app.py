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
# 4. 스마트 종목 검색 헬퍼 및 한글 사전
# ==========================================
KOREAN_STOCK_ALIAS = {
    # 미국 주요 기업 한글명
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
    "모더나": ("MRNA", "Moderna, Inc."),
    "비트코인": ("BTC-USD", "Bitcoin USD"),
    # 한국 주요 기업
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
    "포스코홀딩스": ("005490.KS", "POSCO홀딩스"),
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
# 5. 사이드바 구성
# ==========================================
st.sidebar.title("📊 종목 검색 및 설정")

# 스마트 검색 입력창
search_kw = st.sidebar.text_input(
    "🔍 한글/영문 종목명 또는 티커 검색",
    value="",
    placeholder="예: 템퍼스, 테슬라, 삼전, Apple, NVDA",
    help="한글 기업명(템퍼스, 삼전 등)이나 영문 회사명, 티커 심볼을 자유롭게 입력하세요."
).strip()

final_ticker = "AAPL"

# 검색어 분석 및 자동 매칭
found_options = {}

# 1) 한글 별칭 사전 매칭
kw_clean = search_kw.replace(" ", "").upper()
if kw_clean:
    for alias, (sym, name) in KOREAN_STOCK_ALIAS.items():
        if kw_clean in alias.upper() or alias.upper() in kw_clean:
            found_options[f"⭐ {alias} ({sym}) - {name}"] = sym

# 2) 야후 파이낸스 글로벌 자동완성 API 검색
if search_kw:
    api_results = search_yahoo_finance(search_kw)
    for sym, label in api_results:
        found_options[label] = sym

if found_options:
    selected_item = st.sidebar.selectbox("🎯 검색 결과에서 선택", list(found_options.keys()))
    final_ticker = found_options[selected_item]
else:
    if search_kw:
        # 검색 결과가 없으면 입력값을 대문자 티커로 직접 사용
        final_ticker = search_kw.upper()
    else:
        # 기본 선택 프리셋
        PRESET_STOCKS = {
            "Apple (AAPL)": "AAPL",
            "Tempus AI (TEM)": "TEM",
            "NVIDIA (NVDA)": "NVDA",
            "Tesla (TSLA)": "TSLA",
            "Palantir (PLTR)": "PLTR",
            "삼성전자 (005930.KS)": "005930.KS",
            "SK하이닉스 (000660.KS)": "000660.KS",
            "현대차 (005380.KS)": "005380.KS",
            "NAVER (035420.KS)": "035420.KS",
            "카카오 (035720.KS)": "035720.KS",
        }
        selected_preset = st.sidebar.selectbox("🌟 인기 종목 바로가기", list(PRESET_STOCKS.keys()))
        final_ticker = PRESET_STOCKS[selected_preset]

ticker_input = final_ticker.strip().upper()
st.sidebar.caption(f"선택된 티커: **`{ticker_input}`**")

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
st.sidebar.subheader("📐 차트 작도(드로잉) 도구")

draw_mode_label = st.sidebar.radio(
    "🖱️ 마우스 드래그 동작",
    ["📏 대각선 / 추세선 / 가로선 그리기", "📦 박스권 (사각형) 그리기", "✏️ 자유 곡선 그리기", "🔍 차트 확대 / 축소 (Zoom)", "✋ 차트 이동 (Pan)"],
    index=0
)

draw_mode_map = {
    "📏 대각선 / 추세선 / 가로선 그리기": "drawline",
    "📦 박스권 (사각형) 그리기": "drawrect",
    "✏️ 자유 곡선 그리기": "drawopenpath",
    "🔍 차트 확대 / 축소 (Zoom)": "zoom",
    "✋ 차트 이동 (Pan)": "pan"
}
selected_dragmode = draw_mode_map[draw_mode_label]

col_c1, col_c2 = st.sidebar.columns(2)
with col_c1:
    line_color_choice = st.selectbox(
        "선 색상",
        ["🟡 노랑", "🔵 하늘색", "🔴 빨강", "🟢 초록", "🟣 보라", "⚪ 흰색"],
        index=0
    )
    color_map = {
        "🟡 노랑": "#facc15",
        "🔵 하늘색": "#38bdf8",
        "🔴 빨강": "#ef4444",
        "🟢 초록": "#10b981",
        "🟣 보라": "#c084fc",
        "⚪ 흰색": "#ffffff"
    }
    selected_line_color = color_map[line_color_choice]

with col_c2:
    line_width = st.slider("선 굵기", min_value=1, max_value=5, value=2)

st.sidebar.caption("🗑️ **선 지우기**: 차트 우측 상단 툴바의 **[지우개 아이콘(Erase active shape)]**을 누른 후 지울 선을 클릭하세요.")

st.sidebar.markdown("---")
st.sidebar.subheader("📌 자동 가격 기준선")
show_high_low_lines = st.sidebar.checkbox("최고가 / 최저가 가로선 표시", value=False)
custom_price_line = st.sidebar.number_input("사용자 지정 가격 가로선 (0: 미사용)", min_value=0.0, value=0.0, step=1.0)



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
    height=640,
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
    hovermode="x unified",
    # 사이드바에서 선택한 작도(마우스 드래그) 모드 및 스타일 반영
    dragmode=selected_dragmode,
    newshape=dict(line_color=selected_line_color, line_width=line_width, opacity=0.95)
)

# 마우스 오버 시 가로/세로 십자선 (Spikelines) 활성화
fig.update_xaxes(
    showspikes=True,
    spikemode="across",
    spikesnap="cursor",
    spikedash="dot",
    spikethickness=1,
    spikecolor="#94a3b8"
)
fig.update_yaxes(
    showspikes=True,
    spikemode="across",
    spikesnap="cursor",
    spikedash="dot",
    spikethickness=1,
    spikecolor="#94a3b8"
)

fig.update_yaxes(title_text=f"가격 ({currency})", row=1, col=1)
fig.update_yaxes(title_text="거래량", row=2, col=1)

# 최고가 / 최저가 기준 가로선 추가 (선택 시)
if show_high_low_lines:
    fig.add_hline(
        y=highest_price, line_dash="dash", line_color="#ef4444", line_width=1.5,
        annotation_text=f"최고가: {format_price(highest_price)}", annotation_position="top left",
        row=1, col=1
    )
    fig.add_hline(
        y=lowest_price, line_dash="dash", line_color="#3b82f6", line_width=1.5,
        annotation_text=f"최저가: {format_price(lowest_price)}", annotation_position="bottom left",
        row=1, col=1
    )

# 사용자 지정 가격 가로선 추가 (선택 시)
if custom_price_line > 0:
    fig.add_hline(
        y=custom_price_line, line_dash="dot", line_color="#a855f7", line_width=2,
        annotation_text=f"지정선: {format_price(custom_price_line)}", annotation_position="top right",
        row=1, col=1
    )

# 인터랙티브 툴바 및 드로잉 툴바 설정
chart_config = {
    "modeBarButtonsToAdd": [
        "drawline",       # 직접 선 그리기 (가로선/대각선/추세선)
        "drawrect",       # 박스권/사각형 그리기
        "drawopenpath",   # 자유 곡선 그리기
        "eraseshape"      # 그린 작도선 지우기
    ],
    "scrollZoom": True,
    "displayModeBar": True,  # 툴바 항상 표시
    "displaylogo": False
}

st.plotly_chart(fig, use_container_width=True, config=chart_config)

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
