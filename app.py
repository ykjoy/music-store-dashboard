import streamlit as st
import sqlite3
import os
import pandas as pd
import plotly.express as px

# ── 설정 및 데이터베이스 연결 ────────────────────────────────────────────────
st.set_page_config(page_title="Chinook 데이터 대시보드", page_icon="🎵", layout="wide")

DB_PATH = os.path.join(os.path.dirname(__file__), "chinook.db")

# 데이터를 캐싱하여 매번 DB를 조회하지 않도록 최적화
@st.cache_data
def load_data(sql):
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query(sql, conn)
    conn.close()
    return df

# ── 미리 정의된 시각화 쿼리 (기존 코드와 동일) ──────────────────────────────────
VISUALIZATIONS = [
    {
        "id": "genre_sales",
        "title": "장르별 총 판매액",
        "description": "각 음악 장르가 전체 매출에서 얼마나 비중을 차지하는지 확인합니다.",
        "chart_type": "pie",
        "sql": """SELECT g.Name AS genre, ROUND(SUM(il.UnitPrice * il.Quantity), 2) AS total_sales
                  FROM InvoiceLine il JOIN Track t ON il.TrackId = t.TrackId JOIN Genre g ON t.GenreId = g.GenreId
                  GROUP BY g.Name ORDER BY total_sales DESC LIMIT 10;""",
        "x_key": "genre", "y_key": "total_sales", "x_label": "장르", "y_label": "판매액 (USD)",
    },
    {
        "id": "country_revenue",
        "title": "국가별 매출 Top 10",
        "description": "어느 나라에서 가장 많은 매출이 발생했는지 확인합니다.",
        "chart_type": "bar",
        "sql": """SELECT c.Country, ROUND(SUM(i.Total), 2) AS revenue
                  FROM Invoice i JOIN Customer c ON i.CustomerId = c.CustomerId
                  GROUP BY c.Country ORDER BY revenue DESC LIMIT 10;""",
        "x_key": "Country", "y_key": "revenue", "x_label": "국가", "y_label": "매출 (USD)",
    },
    {
        "id": "monthly_trend",
        "title": "월별 매출 추이",
        "description": "시간 흐름에 따른 매출 변화를 선 그래프로 살펴봅니다.",
        "chart_type": "line",
        "sql": """SELECT STRFTIME('%Y-%m', InvoiceDate) AS month, ROUND(SUM(Total), 2) AS revenue
                  FROM Invoice GROUP BY month ORDER BY month;""",
        "x_key": "month", "y_key": "revenue", "x_label": "연월", "y_label": "매출 (USD)",
    },
    {
        "id": "top_artists",
        "title": "앨범 수 Top 10 아티스트",
        "description": "가장 많은 앨범을 보유한 아티스트를 확인합니다.",
        "chart_type": "bar_horizontal",
        "sql": """SELECT ar.Name AS artist, COUNT(al.AlbumId) AS album_count
                  FROM Artist ar JOIN Album al ON ar.ArtistId = al.ArtistId
                  GROUP BY ar.Name ORDER BY album_count DESC LIMIT 10;""",
        "x_key": "artist", "y_key": "album_count", "x_label": "아티스트", "y_label": "앨범 수",
    },
    {
        "id": "top_customers",
        "title": "구매액 Top 10 고객",
        "description": "지금까지 가장 많은 금액을 결제한 고객 목록을 테이블로 표시합니다.",
        "chart_type": "table",
        "sql": """SELECT c.CustomerId, c.FirstName || ' ' || c.LastName AS customer_name, c.Country, ROUND(SUM(i.Total), 2) AS total_spent
                  FROM Customer c JOIN Invoice i ON c.CustomerId = i.CustomerId
                  GROUP BY c.CustomerId ORDER BY total_spent DESC LIMIT 10;""",
        "x_key": "customer_name", "y_key": "total_spent", "x_label": "고객명", "y_label": "총 구매액 (USD)",
    },
    {
        "id": "track_length",
        "title": "장르별 평균 트랙 길이",
        "description": "장르마다 곡의 평균 길이(분)가 어떻게 다른지 비교합니다.",
        "chart_type": "bar",
        "sql": """SELECT g.Name AS genre, ROUND(AVG(t.Milliseconds) / 60000.0, 2) AS avg_minutes
                  FROM Track t JOIN Genre g ON t.GenreId = g.GenreId
                  GROUP BY g.Name ORDER BY avg_minutes DESC;""",
        "x_key": "genre", "y_key": "avg_minutes", "x_label": "장르", "y_label": "평균 길이 (분)",
    },
    {
        "id": "employee_sales",
        "title": "직원별 담당 고객 매출",
        "description": "각 영업 담당자(직원)가 관리하는 고객들의 총 구매액을 비교합니다.",
        "chart_type": "bar",
        "sql": """SELECT e.FirstName || ' ' || e.LastName AS employee, ROUND(SUM(i.Total), 2) AS managed_sales
                  FROM Employee e JOIN Customer c ON c.SupportRepId = e.EmployeeId JOIN Invoice i ON i.CustomerId = c.CustomerId
                  GROUP BY e.EmployeeId ORDER BY managed_sales DESC;""",
        "x_key": "employee", "y_key": "managed_sales", "x_label": "직원", "y_label": "담당 매출 (USD)",
    },
    {
        "id": "mediatype_dist",
        "title": "미디어 타입별 트랙 수",
        "description": "음원 형식(MP3, AAC 등)에 따른 트랙 분포를 도넛 차트로 확인합니다.",
        "chart_type": "doughnut",
        "sql": """SELECT m.Name AS media_type, COUNT(*) AS track_count
                  FROM Track t JOIN MediaType m ON t.MediaTypeId = m.MediaTypeId
                  GROUP BY m.Name ORDER BY track_count DESC;""",
        "x_key": "media_type", "y_key": "track_count", "x_label": "미디어 타입", "y_label": "트랙 수",
    },
]

# ── 화면 구성 (사이드바 및 메인 화면) ──────────────────────────────────────────
st.sidebar.title("🎵 메뉴")
menu = st.sidebar.radio("원하시는 기능을 선택하세요:", ["📊 대시보드 (시각화)", "💻 자유 SQL 실습"])

if menu == "📊 대시보드 (시각화)":
    st.title("📊 음악 스토어 대시보드")
    
    # 시각화 목록을 딕셔너리 형태로 변환하여 Selectbox에 적용
    viz_dict = {v["title"]: v for v in VISUALIZATIONS}
    selected_title = st.selectbox("조회할 시각화를 선택하세요", list(viz_dict.keys()))
    
    viz = viz_dict[selected_title]
    
    st.subheader(viz["title"])
    st.markdown(f"> {viz['description']}")
    
    # 데이터 로드
    df = load_data(viz["sql"])
    
    # 차트 렌더링 (Plotly 활용)
    chart_type = viz["chart_type"]
    x = viz["x_key"]
    y = viz["y_key"]
    
    if chart_type in ["pie", "doughnut"]:
        hole_size = 0.4 if chart_type == "doughnut" else 0
        fig = px.pie(df, names=x, values=y, hole=hole_size)
        st.plotly_chart(fig, use_container_width=True)
        
    elif chart_type == "bar":
        fig = px.bar(df, x=x, y=y, labels={x: viz["x_label"], y: viz["y_label"]})
        st.plotly_chart(fig, use_container_width=True)
        
    elif chart_type == "bar_horizontal":
        # 가로형 막대그래프는 x와 y를 뒤집어서 적용
        fig = px.bar(df, x=y, y=x, orientation='h', labels={x: viz["y_label"], y: viz["x_label"]})
        fig.update_layout(yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig, use_container_width=True)
        
    elif chart_type == "line":
        fig = px.line(df, x=x, y=y, labels={x: viz["x_label"], y: viz["y_label"]})
        st.plotly_chart(fig, use_container_width=True)
        
    elif chart_type == "table":
        # st.dataframe은 pandas 데이터를 아주 예쁜 표 형태로 그려줍니다.
        st.dataframe(df, use_container_width=True)

    # (옵션) 원본 데이터 보기 토글
    with st.expander("원본 데이터 보기"):
        st.dataframe(df, use_container_width=True)

elif menu == "💻 자유 SQL 실습":
    st.title("💻 자유 SQL 실행기")
    st.info("💡 학생 실습용@@ 데이터베이스 구조를 참고하여 자유롭게 SELECT 문을 작성해 보세요.")
    
    sql_input = st.text_area("SQL 쿼리를 입력하세요:", placeholder="SELECT * FROM Track LIMIT 10;", height=150)
    
    if st.button("실행하기", type="primary"):
        if not sql_input.strip():
            st.warning("⚠️ SQL 쿼리를 입력해 주세요.")
        elif not sql_input.strip().upper().startswith("SELECT"):
            st.error("🚫 안전을 위해 SELECT 문만 실행할 수 있습니다.")
        else:
            try:
                # 사용자가 입력한 쿼리 실행
                df = load_data(sql_input.strip())
                st.success(f"✅ 쿼리 실행 성공! 총 {len(df)}개의 행을 불러왔습니다.")
                st.dataframe(df, use_container_width=True)
            except Exception as e:
                st.error(f"❌ 쿼리 실행 중 오류가 발생했습니다: {e}")
