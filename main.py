import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from utils import fetch_financial_data

# Page Config
st.set_page_config(
    page_title="貸借対照表（B/S）可視化ツール",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load CSS
with open("style.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# Helper Function for Analysis Rendering
def render_company_analysis(ticker, data, key_suffix="", show_metrics=True):
    if "error" in data:
        st.error(f"エラー ({ticker}): {data['error']}\n{data.get('details', '')}")
        return

    # Display Company Name
    company_name = data.get("CompanyName", "不明な企業")
    industry = data.get("Industry", "-")
    
    # Header with animation
    st.markdown(f"""
    <div style="animation: fadeInUp 0.5s ease-out;">
        <h2 style="margin-bottom:0px;">{company_name}</h2>
        <p style="color:gray; font-size:0.9em;">証券コード: {ticker} | 業種: {industry}</p>
    </div>
    """, unsafe_allow_html=True)

    # Data Preparation
    ca = data.get("CurrentAssets", 0)
    nca = data.get("NonCurrentAssets", 0)
    cl = data.get("CurrentLiabilities", 0)
    ncl = data.get("NonCurrentLiabilities", 0)
    na = data.get("NetAssets", 0)
    total_assets = ca + nca
    
    def fmt(val):
        return f"{val/100000000:,.1f}億円" 

    if total_assets == 0:
        st.warning(f"{ticker}: データが見つかりませんでした。")
        return

    # Chart Construction
    fig = go.Figure()
    def rounded_marker(color):
        return dict(color=color, cornerradius=15) 

    # Traces with Custom Data for Click Detection
    # Assets
    fig.add_trace(go.Bar(name='固定資産', x=['資産'], y=[nca], marker=rounded_marker('#0288D1'), 
                         text=fmt(nca), textposition='auto', customdata=['固定資産'], hovertemplate='固定資産: %{y:,.0f}<extra></extra>'))
    fig.add_trace(go.Bar(name='流動資産', x=['資産'], y=[ca], marker=rounded_marker('#4FC3F7'), 
                         text=fmt(ca), textposition='auto', customdata=['流動資産'], hovertemplate='流動資産: %{y:,.0f}<extra></extra>'))
    
    # Liabilities
    fig.add_trace(go.Bar(name='純資産', x=['負債・純資産'], y=[na], marker=rounded_marker('#01579B'), 
                         text=fmt(na), textposition='auto', customdata=['純資産'], hovertemplate='純資産: %{y:,.0f}<extra></extra>'))
    fig.add_trace(go.Bar(name='固定負債', x=['負債・純資産'], y=[ncl], marker=rounded_marker('#78909C'), 
                         text=fmt(ncl), textposition='auto', customdata=['固定負債'], hovertemplate='固定負債: %{y:,.0f}<extra></extra>'))
    fig.add_trace(go.Bar(name='流動負債', x=['負債・純資産'], y=[cl], marker=rounded_marker('#B0BEC5'), 
                         text=fmt(cl), textposition='auto', customdata=['流動負債'], hovertemplate='流動負債: %{y:,.0f}<extra></extra>'))
    
    fig.update_layout(
        barmode='stack',
        showlegend=True,
        height=400 if not show_metrics else 500,
        margin=dict(l=20, r=20, t=30, b=20),
        paper_bgcolor='white', 
        plot_bgcolor='white',
        font=dict(size=14, family="Noto Sans JP", color="#333333"),
        xaxis=dict(tickfont=dict(color="#333333", size=14), linecolor="#e0e0e0"),
        yaxis=dict(tickfont=dict(color="#333333"), title=dict(font=dict(color="#333333")), showgrid=True, gridcolor="#f0f0f0"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(color="#333333")),
        clickmode='event+select' # Enable clicking
    )

    if show_metrics:
        col1, col2 = st.columns([4, 1])
        with col1:
             st.markdown("#### 資産・負債の構成")
             # Capture selection
             selection = st.plotly_chart(fig, use_container_width=True, key=f"chart_{ticker}_{key_suffix}", on_select="rerun", selection_mode="points")
             
             # Drill Down Logic
             detail_content = None
             if selection and selection["selection"]["points"]:
                 point = selection["selection"]["points"][0]
                 category = point["customdata"][0] if "customdata" in point else point["legendgroup"]
                 
                 if category == "流動資産":
                     detail_content = {
                         "title": "流動資産の詳細",
                         "items": [
                             ("現金・預金", data.get("Cash", 0)),
                             ("受取手形・売掛金", data.get("Receivables", 0)),
                             ("棚卸資産", data.get("Inventory", 0)),
                             ("その他", ca - (data.get("Cash",0)+data.get("Receivables",0)+data.get("Inventory",0)))
                         ]
                     }
                 elif category == "固定資産":
                     detail_content = {
                         "title": "固定資産の詳細",
                         "items": [
                             ("有形固定資産", data.get("PPE", 0)),
                             ("無形固定資産", data.get("Intangible", 0)),
                             ("投資その他の資産", data.get("Investments", 0)),
                         ]
                     }
                 elif category in ["固定負債", "流動負債"]:
                     # Show Debt Info
                     interest_debt = data.get("InterestDebt", 0)
                     detail_content = {
                         "title": "負債の詳細情報",
                         "items": [
                             ("有利子負債合計", interest_debt),
                             ("その他の負債", (cl + ncl) - interest_debt)
                         ]
                     }
                 elif category == "純資産":
                     detail_content = {
                         "title": "純資産の詳細",
                         "items": [
                             ("利益剰余金", data.get("RetainedEarnings", 0)),
                             ("その他", na - data.get("RetainedEarnings", 0))
                         ]
                     }

             if detail_content:
                 st.markdown(f"""
                 <div style="background-color:#F5F5F5; padding:15px; border-radius:8px; margin-top:10px; border-left: 5px solid #0288D1; animation: fadeInUp 0.3s ease;">
                    <h5 style="margin:0 0 10px 0;">🔍 {detail_content['title']}</h5>
                    <div style="display:flex; justify-content:space-around; flex-wrap:wrap;">
                        {"".join([f'<div style="text-align:center; min-width:100px; margin:5px;"><div style="font-size:0.8em; color:#666;">{tag}</div><div style="font-weight:bold;">{fmt(val)}</div></div>' for tag, val in detail_content['items']])}
                    </div>
                 </div>
                 """, unsafe_allow_html=True)


        with col2:
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
            
        # Analysis Card
        analysis_text = ""
        if equity_ratio > 50:
            analysis_text += "<p><strong>✅ 高い安全性</strong><br>自己資本比率が50%を超えており、財務基盤は非常に強固です。</p>"
        elif equity_ratio >= 30:
            analysis_text += "<p><strong>ℹ️ 標準的な水準</strong><br>自己資本比率は平均的です。成長投資とのバランスが取れています。</p>"
        else:
            analysis_text += "<p><strong>⚠️ 改善の余地あり</strong><br>自己資本比率が30%を下回っています。借入金への依存度が高いため、金利上昇リスクなどに注意が必要です。</p>"
        
        st.markdown(f"""<div class="material-card" style="padding: 20px; animation-delay: 0.2s;">
<h4 style="margin: 0 0 10px 0; color: #333;">コメント</h4>
<div style="font-size: 0.95em; line-height: 1.6;">
{analysis_text}
</div>
</div>""", unsafe_allow_html=True)

    else:
        # Comparison Mode: Just Chart
        st.markdown("#### 資産・負債の構成")
        selection = st.plotly_chart(fig, use_container_width=True, key=f"chart_{ticker}_{key_suffix}", on_select="rerun", selection_mode="points")
        
        if selection and selection["selection"]["points"]:
             point = selection["selection"]["points"][0]
             category = point["customdata"][0] if "customdata" in point else point["legendgroup"]
             
             detail_content = None
             if category == "流動資産":
                 detail_content = {
                     "title": "流動資産の詳細",
                     "items": [
                         ("現金・預金", data.get("Cash", 0)),
                         ("受取手形・売掛金", data.get("Receivables", 0)),
                         ("棚卸資産", data.get("Inventory", 0)),
                         ("その他", ca - (data.get("Cash",0)+data.get("Receivables",0)+data.get("Inventory",0)))
                     ]
                 }
             elif category == "固定資産":
                 detail_content = {
                     "title": "固定資産の詳細",
                     "items": [
                         ("有形固定資産", data.get("PPE", 0)),
                         ("無形固定資産", data.get("Intangible", 0)),
                         ("投資その他の資産", data.get("Investments", 0)),
                     ]
                 }
             elif category in ["固定負債", "流動負債"]:
                 interest_debt = data.get("InterestDebt", 0)
                 detail_content = {
                     "title": "負債の詳細情報",
                     "items": [
                         ("有利子負債合計", interest_debt),
                         ("その他の負債", (cl + ncl) - interest_debt)
                     ]
                 }
             elif category == "純資産":
                 detail_content = {
                     "title": "純資産の詳細",
                     "items": [
                         ("利益剰余金", data.get("RetainedEarnings", 0)),
                         ("その他", na - data.get("RetainedEarnings", 0))
                     ]
                 }

             if detail_content:
                 st.markdown(f"""
                 <div style="background-color:#F5F5F5; padding:10px; border-radius:8px; margin-top:5px; border-left: 4px solid #0288D1; font-size:0.9em;">
                    <div style="font-weight:bold; margin-bottom:5px;">🔍 {detail_content['title']}</div>
                    <div style="display:flex; justify-content:space-between; flex-wrap:wrap;">
                        {"".join([f'<div style="margin-right:10px;"><span style="color:#666;">{tag}:</span> <b>{fmt(val)}</b></div>' for tag, val in detail_content['items']])}
                    </div>
                 </div>
                 """, unsafe_allow_html=True)

# Application Header
st.title("📊 貸借対照表（B/S）可視化ツール")
st.markdown("証券コードを入力して、企業の財務健全性を可視化します。")

# Sidebar
st.sidebar.header("設定")
ticker1 = st.sidebar.text_input("証券コード (メイン)", value="") # No default

# Comparison Toggle
compare_mode = st.sidebar.checkbox("他社と比較する", value=False)
ticker2 = ""
if compare_mode:
    ticker2 = st.sidebar.text_input("証券コード (比較対象)", value="") # No default

analyze_btn = st.sidebar.button("分析開始", type="primary")

# Main Area
if analyze_btn:
    if not ticker1:
         st.warning("証券コードを入力してください。")
    else:
        import concurrent.futures

        # Progress Logic for Parallel Fetch
        # We can't easily share the single progress bar with granular updates from two threads.
        # So we'll disable granular progress inside the function for the parallel run 
        # and just show a global spinner/progress.
        
        progress_bar = st.progress(0, text="データ取得を開始します...")
        
        def fetch_wrapper(t):
            return fetch_financial_data(t, progress_callback=None)

        data1 = None
        data2 = None

        if compare_mode and ticker2:
            progress_bar.progress(30, text=f"2社同時検索・解析中... ({ticker1}, {ticker2})")
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                future1 = executor.submit(fetch_wrapper, ticker1)
                future2 = executor.submit(fetch_wrapper, ticker2)
                
                data1 = future1.result()
                data2 = future2.result()
            
            progress_bar.progress(100, text="完了")
        
        else:
            # Single mode: Use granular progress
            def update_ui_progress(percent, text):
                progress_bar.progress(percent, text=text)
            
            data1 = fetch_financial_data(ticker1, progress_callback=update_ui_progress)
        
        progress_bar.empty()
        
        # Render
        if compare_mode and data2:
            # Side by side Comparison - Charts Only
            main_col1, main_col2 = st.columns(2)
            
            with main_col1:
                render_company_analysis(ticker1, data1, "1", show_metrics=False)
                
            with main_col2:
                render_company_analysis(ticker2, data2, "2", show_metrics=False)
            
            # Unified Comparison Summary
            st.markdown("---")
            st.subheader("📊 比較分析サマリー")
            
            # Calculate Metrics
            def get_metrics(d):
                ta = d.get("TotalAssets", 0)
                na = d.get("NetAssets", 0)
                ca = d.get("CurrentAssets", 0)
                cl = d.get("CurrentLiabilities", 0)
                er = (na / ta * 100) if ta > 0 else 0
                cr = (ca / cl * 100) if cl > 0 else 0
                return ta, na, er, cr

            ta1, na1, er1, cr1 = get_metrics(data1)
            ta2, na2, er2, cr2 = get_metrics(data2)
            
            # Generate Insight
            c1_name = data1.get('CompanyName')
            c2_name = data2.get('CompanyName')
            
            insight = ""
            # Size
            if ta1 > ta2 * 1.5:
                insight += f"<li>規模: <strong>{c1_name}</strong> は {c2_name} よりも資産規模が大きく上回っています。</li>"
            elif ta2 > ta1 * 1.5:
                insight += f"<li>規模: <strong>{c2_name}</strong> は {c1_name} よりも資産規模が大きく上回っています。</li>"
            else:
                insight += f"<li>規模: 両社の資産規模は比較的近いです。</li>"
                
            # Safety
            if er1 > er2 + 10:
                insight += f"<li>安全性: <strong>{c1_name}</strong> (自己資本比率 {er1:.1f}%) の方が財務的な安全性が高いです。</li>"
            elif er2 > er1 + 10:
                insight += f"<li>安全性: <strong>{c2_name}</strong> (自己資本比率 {er2:.1f}%) の方が財務的な安全性が高いです。</li>"
            else:
                insight += f"<li>安全性: 両社の財務安全性（自己資本比率）は同水準です。</li>"

            # Table HTML
            def fmt_val(v): return f"{v/100000000:,.0f}億円"
            
            st.markdown(f"""
            <div class="material-card">
                <table style="width:100%; border-collapse: collapse;">
                    <tr style="border-bottom: 2px solid #eee;">
                        <th style="text-align:left; padding:10px; color:#666;">項目</th>
                        <th style="text-align:right; padding:10px; color:#333;">{c1_name}</th>
                        <th style="text-align:right; padding:10px; color:#333;">{c2_name}</th>
                        <th style="text-align:center; padding:10px; color:#999;">判定</th>
                    </tr>
                    <tr style="border-bottom: 1px solid #f0f0f0;">
                        <td style="padding:10px; font-weight:bold; color:#0277BD;">資産合計 (Size)</td>
                        <td style="text-align:right; padding:10px;">{fmt_val(ta1)}</td>
                        <td style="text-align:right; padding:10px;">{fmt_val(ta2)}</td>
                        <td style="text-align:center; padding:10px;">{"👈 Larger" if ta1 > ta2 else "Larger 👉"}</td>
                    </tr>
                    <tr style="border-bottom: 1px solid #f0f0f0;">
                        <td style="padding:10px; font-weight:bold; color:#0277BD;">自己資本比率 (Safety)</td>
                        <td style="text-align:right; padding:10px;">{er1:.1f}%</td>
                        <td style="text-align:right; padding:10px;">{er2:.1f}%</td>
                        <td style="text-align:center; padding:10px;">{"👈 High" if er1 > er2 else "High 👉"}</td>
                    </tr>
                    <tr style="border-bottom: 1px solid #f0f0f0;">
                        <td style="padding:10px; font-weight:bold; color:#0277BD;">流動比率 (Liquidity)</td>
                        <td style="text-align:right; padding:10px;">{cr1:.1f}%</td>
                        <td style="text-align:right; padding:10px;">{cr2:.1f}%</td>
                        <td style="text-align:center; padding:10px;">{"👈 High" if cr1 > cr2 else "High 👉"}</td>
                    </tr>
                </table>
                <div style="margin-top: 20px; background-color: #E1F5FE; padding: 15px; border-radius: 8px;">
                    <h5 style="margin:0 0 10px 0; color:#01579B;">比較コメント</h5>
                    <ul style="margin:0; padding-left:20px; line-height:1.6; color:#0277BD;">
                        {insight}
                    </ul>
                </div>
            </div>
            """, unsafe_allow_html=True)

        else:
            # Single View
            render_company_analysis(ticker1, data1, "1", show_metrics=True)

else:
    # Empty State with Animation
    st.markdown("""
    <div style="text-align: center; padding: 50px; animation: fadeInUp 0.8s ease-out;">
        <h3 style="color: #ccc;">Enter Ticker to Start</h3>
        <p style="color: #999;">証券コードを入力して、分析を開始してください。</p>
    </div>
    """, unsafe_allow_html=True)
