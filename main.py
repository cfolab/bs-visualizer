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
if analyze_btn:
    with st.spinner("財務データを取得中...（これには数秒かかる場合があります）"):
        # Fetch Data
        data = fetch_financial_data(ticker)
        
        if "error" in data:
            st.error(f"エラーが発生しました: {data['error']}")
            if "details" in data:
                st.caption(f"詳細: {data['details']}")
        else:
            # Display Company Name
            company_name = data.get("CompanyName", "不明な企業")
            st.markdown(f"### {company_name} ({ticker}) の分析結果")

            # Data Preparation
            ca = data.get("CurrentAssets", 0)
            nca = data.get("NonCurrentAssets", 0)
            cl = data.get("CurrentLiabilities", 0)
            ncl = data.get("NonCurrentLiabilities", 0)
            na = data.get("NetAssets", 0)
            
            total_assets = ca + nca
            total_liab_equity = cl + ncl + na
            
            # Formatting helpers
            def fmt(val):
                return f"{val/100000000:,.1f}億円" # Billions
            
            # Sanity Check
            if total_assets == 0:
                st.warning("有効な資産データが見つかりませんでした。")
            else:
                 # Comparison logic
                diff = abs(total_assets - total_liab_equity)
                if diff > total_assets * 0.05:
                    st.warning(f"注: 資産合計と負債・純資産合計が一致しません（差額: {diff/1e8:.1f}億円）。データ取得上の誤差の可能性があります。")

                # Visualization
                # Visuals
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    st.markdown("#### バランスシート構造")
                    
                    fig = go.Figure()
                    
                    # Common marker settings with rounded corners
                    def rounded_marker(color):
                        return dict(color=color, cornerradius=15) # 15px radius

                    # Assets Column (Left)
                    fig.add_trace(go.Bar(
                        name='流動資産',
                        x=['資産の部'], y=[ca],
                        marker=rounded_marker('#FFF8DC'), # Light Yellow/Beige
                        text=fmt(ca), textposition='auto',
                        hovertemplate='流動資産: %{y:,.0f}<extra></extra>'
                    ))
                    
                    fig.add_trace(go.Bar(
                        name='固定資産',
                        x=['資産の部'], y=[nca],
                        marker=rounded_marker('#E0FFFF'), # Light Cyan
                        text=fmt(nca), textposition='auto',
                        hovertemplate='固定資産: %{y:,.0f}<extra></extra>'
                    ))
                    
                    # Liabilities+Equity Column (Right)
                    # User requested: Net Assets at bottom, Liabilities at top.
                    
                    # 1. Net Assets (Bottom)
                    fig.add_trace(go.Bar(
                        name='純資産',
                        x=['負債・純資産の部'], y=[na],
                        marker=rounded_marker('#90EE90'), # Light Green
                        text=fmt(na), textposition='auto',
                        hovertemplate='純資産: %{y:,.0f}<extra></extra>'
                    ))
                    
                    # 2. Fixed Liabilities (Middle)
                    fig.add_trace(go.Bar(
                        name='固定負債',
                        x=['負債・純資産の部'], y=[ncl],
                        marker=rounded_marker('#FFA07A'), # Light Salmon
                        text=fmt(ncl), textposition='auto',
                        hovertemplate='固定負債: %{y:,.0f}<extra></extra>'
                    ))
                    
                    # 3. Current Liabilities (Top)
                    fig.add_trace(go.Bar(
                        name='流動負債',
                        x=['負債・純資産の部'], y=[cl],
                        marker=rounded_marker('#FFDAB9'), # Peach Puff
                        text=fmt(cl), textposition='auto',
                        hovertemplate='流動負債: %{y:,.0f}<extra></extra>'
                    ))
                    
                    # Layout Updates
                    fig.update_layout(
                        barmode='stack',
                        title_text=f"貸借対照表構成 ({company_name})",
                        yaxis_title="金額 (円)",
                        showlegend=True,
                        height=600,
                        paper_bgcolor='rgba(255,255,255,0)', # Transparent
                        plot_bgcolor='rgba(255,255,255,0)',
                        font=dict(size=14, color="black") # Plain black text
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)
                
                with col2:
                    st.markdown("#### 主要指標")
                    
                    # Metrics
                    equity_ratio = (na / total_assets) * 100 if total_assets > 0 else 0
                    current_ratio = (ca / cl) * 100 if cl > 0 else 0
                    
                    st.metric("自己資本比率", f"{equity_ratio:.1f}%")
                    st.metric("流動比率", f"{current_ratio:.1f}%")
                    st.metric("資産合計", fmt(total_assets))
                    st.metric("純資産", fmt(na))

                # AI Analysis Mock
                st.markdown("---")
                st.subheader("💡 AI 簡易分析 (自動生成)")
                
                analysis_text = ""
                if equity_ratio > 50:
                    analysis_text += "✅ **高い安全性**: 自己資本比率が50%を超えており、財務体質は非常に健全です。長期的な安定性が期待できます。\n\n"
                elif equity_ratio > 20:
                    analysis_text += "ℹ️ **標準的な安全性**: 自己資本比率は標準的な水準です。極端なリスクは見当たりませんが、業界平均との比較が推奨されます。\n\n"
                else:
                    analysis_text += "⚠️ **注意が必要**: 自己資本比率が低めです。借入への依存度が高い可能性があります。\n\n"
                    
                if current_ratio > 200:
                    analysis_text += "✅ **高い短期支払い能力**: 流動比率が200%を超えており、短期的な資金繰りに全く問題はありません。\n\n"
                elif current_ratio > 100:
                    analysis_text += "ℹ️ **安定した支払い能力**: 流動資産が流動負債を上回っており、直近の支払いに懸念はありません。\n\n"
                else:
                    analysis_text += "⚠️ **資金繰りに注意**: 流動比率が100%を下回っています。短期的な債務返済において、手元資金が不足するリスクがあります。\n\n"
                
                st.info(analysis_text)
                
                # Expander for raw data
                with st.expander("生データを表示"):
                    st.json(data)

else:
    st.info("証券コードを入力し、「分析開始」をクリックしてください。")
