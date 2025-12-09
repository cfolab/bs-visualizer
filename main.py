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

# Application Header
st.title("📊 貸借対照表（B/S）ビジュアライザー")
st.markdown("証券コードを入力して、企業の財務健全性を可視化します。")

# Sidebar
st.sidebar.header("設定")
ticker = st.sidebar.text_input("証券コード (例: 7203)", value="7203")
analyze_btn = st.sidebar.button("分析開始", type="primary")

# Main Area
# Main Area
if analyze_btn:
    with st.spinner("財務データを取得中..."):
        # Fetch Data
        data = fetch_financial_data(ticker)
        
        if "error" in data:
            st.error(f"エラー: {data['error']}\n{data.get('details', '')}")
        else:
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
            total_liab_equity = cl + ncl + na
            
            def fmt(val):
                return f"{val/100000000:,.1f}億円" 

            if total_assets == 0:
                st.warning("データが見つかりませんでした。")
            else:
                # Layout
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    # Card Wrapper Start
                    st.markdown('<div class="material-card">', unsafe_allow_html=True)
                    st.markdown("#### 資産・負債の構成")
                    
                    fig = go.Figure()
                    def rounded_marker(color):
                        return dict(color=color, cornerradius=15) 

                    # Assets Column (Left)
                    fig.add_trace(go.Bar(name='流動資産', x=['資産'], y=[ca], marker=rounded_marker('#E3F2FD'), text=fmt(ca), textposition='auto', hovertemplate='流動資産: %{y:,.0f}<extra></extra>'))
                    fig.add_trace(go.Bar(name='固定資産', x=['資産'], y=[nca], marker=rounded_marker('#BBDEFB'), text=fmt(nca), textposition='auto', hovertemplate='固定資産: %{y:,.0f}<extra></extra>'))
                    
                    # Liabilities (Right) - Order: NetAssets(Bottom) -> Fixed -> Current
                    fig.add_trace(go.Bar(name='純資産', x=['負債・純資産'], y=[na], marker=rounded_marker('#C8E6C9'), text=fmt(na), textposition='auto', hovertemplate='純資産: %{y:,.0f}<extra></extra>'))
                    fig.add_trace(go.Bar(name='固定負債', x=['負債・純資産'], y=[ncl], marker=rounded_marker('#FFCCBC'), text=fmt(ncl), textposition='auto', hovertemplate='固定負債: %{y:,.0f}<extra></extra>'))
                    fig.add_trace(go.Bar(name='流動負債', x=['負債・純資産'], y=[cl], marker=rounded_marker('#FFE0B2'), text=fmt(cl), textposition='auto', hovertemplate='流動負債: %{y:,.0f}<extra></extra>'))
                    
                    fig.update_layout(
                        barmode='stack',
                        showlegend=True,
                        height=500,
                        margin=dict(l=20, r=20, t=30, b=20),
                        paper_bgcolor='rgba(0,0,0,0)',
                        plot_bgcolor='rgba(0,0,0,0)',
                        font=dict(size=14, family="Noto Sans JP", color="#333"),
                        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                    )
                    st.plotly_chart(fig, use_container_width=True)
                    st.markdown('</div>', unsafe_allow_html=True) # Card End

                with col2:
                    # Metrics Card
                    equity_ratio = (na / total_assets) * 100 if total_assets > 0 else 0
                    current_ratio = (ca / cl) * 100 if cl > 0 else 0
                    
                    st.markdown('<div class="material-card">', unsafe_allow_html=True)
                    st.markdown("#### 主要指標")
                    st.metric("自己資本比率", f"{equity_ratio:.1f}%", delta_color="normal")
                    st.metric("流動比率", f"{current_ratio:.1f}%")
                    st.markdown("---")
                    st.metric("資産合計", fmt(total_assets))
                    st.metric("純資産", fmt(na))
                    st.markdown('</div>', unsafe_allow_html=True)


                # Analysis Card
                st.markdown('<div class="material-card" style="animation-delay: 0.2s;">', unsafe_allow_html=True)
                st.subheader("💡 AI 簡易分析")
                
                analysis_text = ""
                if equity_ratio > 50:
                    analysis_text += "✅ **高い安全性 (High Stability)**\n\n自己資本比率が50%を超えており、財務基盤は非常に強固です。"
                elif equity_ratio > 20:
                    analysis_text += "ℹ️ **標準的な水準 (Standard)**\n\n自己資本比率は平均的です。成長投資とのバランスが取れています。"
                else:
                    analysis_text += "⚠️ **改善の余地あり (Low Stability)**\n\n自己資本比率が低めです。財務レバレッジを活用している可能性がありますが、リスク管理に注意が必要です。"
                
                st.info(analysis_text)
                st.markdown('</div>', unsafe_allow_html=True)

else:
    # Empty State with Animation
    st.markdown("""
    <div style="text-align: center; padding: 50px; animation: fadeInUp 0.8s ease-out;">
        <h3 style="color: #ccc;">Enter Ticker to Start</h3>
        <p style="color: #999;">証券コードを入力して、分析を開始してください。</p>
    </div>
    """, unsafe_allow_html=True)
