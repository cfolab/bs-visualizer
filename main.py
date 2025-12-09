import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from utils import fetch_financial_data

# Page Config
st.set_page_config(
    page_title="貸借対照表（B/S）ビジュアライザー",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load CSS
with open("style.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# Helper Function for Analysis Rendering
def render_company_analysis(ticker, data, key_suffix=""):
    if "error" in data:
        st.error(f"エラー ({ticker}): {data['error']}\n{data.get('details', '')}")
        return

    # Display Company Name
    company_name = data.get("CompanyName", "不明な企業")
    
    # Header with animation
    st.markdown(f"""
    <div style="animation: fadeInUp 0.5s ease-out;">
        <h2 style="margin-bottom:0px;">{company_name}</h2>
        <p style="color:gray; font-size:0.9em;">証券コード: {ticker}</p>
    </div>
    """, unsafe_allow_html=True)

    # Data Preparation
    ca = data.get("CurrentAssets", 0)
    nca = data.get("NonCurrentAssets", 0)
    cl = data.get("CurrentLiabilities", 0)
    ncl = data.get("NonCurrentLiabilities", 0)
    na = data.get("NetAssets", 0)
    total_assets = ca + nca
    # total_liab_equity = cl + ncl + na # Unused but good for debug
    
    def fmt(val):
        return f"{val/100000000:,.1f}億円" 

    if total_assets == 0:
        st.warning(f"{ticker}: データが見つかりませんでした。")
        return

    # Layout (4:1 ratio to make metrics narrow)
    # Note: When in side-by-side mode, this 4:1 splits the *half* screen.
    col1, col2 = st.columns([4, 1]) 
    
    with col1:
        # Chart Section
        st.markdown("#### 資産・負債の構成")
        
        fig = go.Figure()
        def rounded_marker(color):
            return dict(color=color, cornerradius=15) 

        # Assets Column (Left) - Professional Blue Theme
        # Stack Order: Bottom -> Top
        # Non-current Assets: Medium Blue (Base)
        fig.add_trace(go.Bar(name='固定資産', x=['資産'], y=[nca], marker=rounded_marker('#0288D1'), text=fmt(nca), textposition='auto', hovertemplate='固定資産: %{y:,.0f}<extra></extra>'))
        # Current Assets: Light Blue (Top)
        fig.add_trace(go.Bar(name='流動資産', x=['資産'], y=[ca], marker=rounded_marker('#4FC3F7'), text=fmt(ca), textposition='auto', hovertemplate='流動資産: %{y:,.0f}<extra></extra>'))
        
        # Liabilities (Right) - Order: NetAssets(Bottom) -> Fixed -> Current
        fig.add_trace(go.Bar(name='純資産', x=['負債・純資産'], y=[na], marker=rounded_marker('#01579B'), text=fmt(na), textposition='auto', hovertemplate='純資産: %{y:,.0f}<extra></extra>'))
        fig.add_trace(go.Bar(name='固定負債', x=['負債・純資産'], y=[ncl], marker=rounded_marker('#78909C'), text=fmt(ncl), textposition='auto', hovertemplate='固定負債: %{y:,.0f}<extra></extra>'))
        fig.add_trace(go.Bar(name='流動負債', x=['負債・純資産'], y=[cl], marker=rounded_marker('#B0BEC5'), text=fmt(cl), textposition='auto', hovertemplate='流動負債: %{y:,.0f}<extra></extra>'))
        
        fig.update_layout(
            barmode='stack',
            showlegend=True,
            height=500,
            margin=dict(l=20, r=20, t=30, b=20),
            paper_bgcolor='white', 
            plot_bgcolor='white',
            font=dict(size=14, family="Noto Sans JP", color="#333333"),
            # Explicitly style axes to ensure visibility
            xaxis=dict(
                tickfont=dict(color="#333333", size=14, family="Noto Sans JP"),
                linecolor="#e0e0e0"
            ),
            yaxis=dict(
                tickfont=dict(color="#333333"),
                title=dict(font=dict(color="#333333")),
                showgrid=True,
                gridcolor="#f0f0f0"
            ),
            legend=dict(
                orientation="h", 
                yanchor="bottom", y=1.02, 
                xanchor="right", x=1,
                font=dict(color="#333333")
            )
        )
        st.plotly_chart(fig, use_container_width=True, key=f"chart_{ticker}_{key_suffix}")

    with col2:
        # Metrics Card - Pure HTML for Left Alignment and Tight Control
        equity_ratio = (na / total_assets) * 100 if total_assets > 0 else 0
        current_ratio = (ca / cl) * 100 if cl > 0 else 0
        
        st.markdown(f"""<div class="material-card" style="padding: 20px; text-align: left;">
<h4 style="margin: 0 0 15px 0; color: #333;">主要指標</h4>
<div style="margin-bottom: 12px;">
<div style="color: #666; font-size: 0.85em;">自己資本比率</div>
<div style="color: #333; font-size: 1.25em; font-weight: bold;">{equity_ratio:.1f}%</div>
</div>
<div style="margin-bottom: 12px;">
<div style="color: #666; font-size: 0.85em;">流動比率</div>
<div style="color: #333; font-size: 1.25em; font-weight: bold;">{current_ratio:.1f}%</div>
</div>
<hr style="margin: 15px 0; border-top: 1px solid #eee;">
<div style="margin-bottom: 12px;">
<div style="color: #666; font-size: 0.85em;">資産合計</div>
<div style="color: #333; font-size: 1.1em; font-weight: bold;">{fmt(total_assets)}</div>
</div>
<div>
<div style="color: #666; font-size: 0.85em;">純資産</div>
<div style="color: #333; font-size: 1.1em; font-weight: bold;">{fmt(na)}</div>
</div>
</div>""", unsafe_allow_html=True)


    # Analysis Card - Pure HTML
    analysis_text = ""
    if equity_ratio > 50:
        analysis_text += "<p><strong>✅ 高い安全性</strong><br>自己資本比率が50%を超えており、財務基盤は非常に強固です。</p>"
    elif equity_ratio > 20:
        analysis_text += "<p><strong>ℹ️ 標準的な水準</strong><br>自己資本比率は平均的です。成長投資とのバランスが取れています。</p>"
    else:
        analysis_text += "<p><strong>⚠️ 改善の余地あり</strong><br>自己資本比率が低めです。リスク管理に注意が必要です。</p>"
    
    st.markdown(f"""<div class="material-card" style="padding: 20px; animation-delay: 0.2s;">
<h4 style="margin: 0 0 10px 0; color: #333;">💡 AI 簡易分析</h4>
<div style="font-size: 0.95em; line-height: 1.6;">
{analysis_text}
</div>
</div>""", unsafe_allow_html=True)


# Application Header
st.title("📊 貸借対照表（B/S）ビジュアライザー")
st.markdown("証券コードを入力して、企業の財務健全性を可視化します。")

# Sidebar
st.sidebar.header("設定")
ticker1 = st.sidebar.text_input("証券コード (メイン)", value="7203")

# Comparison Toggle
compare_mode = st.sidebar.checkbox("他社と比較する", value=False)
ticker2 = ""
if compare_mode:
    ticker2 = st.sidebar.text_input("証券コード (比較対象)", value="6758") # Default Sony

analyze_btn = st.sidebar.button("分析開始", type="primary")

# Main Area
if analyze_btn:
    with st.spinner("財務データを取得中..."):
        # Fetch Data 1
        data1 = fetch_financial_data(ticker1)
        data2 = None
        
        if compare_mode and ticker2:
            data2 = fetch_financial_data(ticker2)
        
        # Render
        if compare_mode and data2:
            # Side by side Comparison
            main_col1, main_col2 = st.columns(2)
            
            with main_col1:
                render_company_analysis(ticker1, data1, "1")
                
            with main_col2:
                render_company_analysis(ticker2, data2, "2")
        else:
            # Single View
            render_company_analysis(ticker1, data1, "1")

else:
    # Empty State with Animation
    st.markdown("""
    <div style="text-align: center; padding: 50px; animation: fadeInUp 0.8s ease-out;">
        <h3 style="color: #ccc;">Enter Ticker to Start</h3>
        <p style="color: #999;">証券コードを入力して、分析を開始してください。</p>
    </div>
    """, unsafe_allow_html=True)
