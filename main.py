import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from utils import fetch_financial_data

# Page Config
st.set_page_config(
    page_title="Balance Sheet Visualizer",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load CSS
with open("style.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# Application Header
st.title("📊 Balance Sheet Visualizer")
st.markdown("Enter a ticker code to visualize the company's financial health.")

# Sidebar
st.sidebar.header("Input")
ticker = st.sidebar.text_input("Ticker Code (e.g., 7203)", value="7203")
analyze_btn = st.sidebar.button("Analyze")

# Main Area
if analyze_btn:
    with st.spinner("Fetching financial data from EDINET..."):
        # Fetch Data
        data = fetch_financial_data(ticker)
        
        if "error" in data:
            st.error(f"Error: {data['error']}")
            if "details" in data:
                st.caption(f"Details: {data['details']}")
        else:
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
                return f"¥{val/100000000:,.1f}B" # Billions
            
            # Visualization
            # Create two stacked bars: Assets vs Liabilities+Equity
            
            fig = go.Figure()
            
            # Assets Column (Left)
            fig.add_trace(go.Bar(
                name='Current Assets',
                x=['Assets'], y=[ca],
                marker_color='#FFF8DC', # Light Yellow/Beige
                text=fmt(ca), textposition='auto',
                hovertemplate='Current Assets: %{y:,.0f}<extra></extra>'
            ))
            
            fig.add_trace(go.Bar(
                name='Non-Current Assets',
                x=['Assets'], y=[nca],
                marker_color='#E0FFFF', # Light Cyan
                text=fmt(nca), textposition='auto',
                hovertemplate='Non-Current Assets: %{y:,.0f}<extra></extra>'
            ))
            
            # Liabilities+Equity Column (Right)
            fig.add_trace(go.Bar(
                name='Current Liabilities',
                x=['Liabilities & Equity'], y=[cl],
                marker_color='#FFDAB9', # Peach Puff
                text=fmt(cl), textposition='auto',
                hovertemplate='Current Liabilities: %{y:,.0f}<extra></extra>'
            ))
            
            fig.add_trace(go.Bar(
                name='Non-Current Liabilities',
                x=['Liabilities & Equity'], y=[ncl],
                marker_color='#FFA07A', # Light Salmon
                text=fmt(ncl), textposition='auto',
                hovertemplate='Non-Current Liabilities: %{y:,.0f}<extra></extra>'
            ))
            
            fig.add_trace(go.Bar(
                name='Net Assets',
                x=['Liabilities & Equity'], y=[na],
                marker_color='#90EE90', # Light Green
                text=fmt(na), textposition='auto',
                hovertemplate='Net Assets: %{y:,.0f}<extra></extra>'
            ))
            
            # Layout Updates
            fig.update_layout(
                barmode='stack',
                title_text=f"Balance Sheet Structure ({ticker})",
                yaxis_title="Amount (JPY)",
                showlegend=True,
                height=600,
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(size=14)
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # AI Analysis Mock
            st.markdown("---")
            st.subheader("💡 AI Analyst Insights")
            
            equity_ratio = (na / total_assets) * 100 if total_assets > 0 else 0
            current_ratio = (ca / cl) * 100 if cl > 0 else 0
            
            st.markdown(f"""
            **Financial Health Summary:**
            
            - **Equity Ratio**: `{equity_ratio:.1f}%` 
              - *Interpretation*: {"High stability" if equity_ratio > 50 else "Standard leverage" if equity_ratio > 30 else "High leverage"}. Values above 50% generally indicate a financially stable company.
            - **Current Ratio**: `{current_ratio:.1f}%`
              - *Interpretation*: {"Excellent short-term liquidity" if current_ratio > 200 else "Good liquidity" if current_ratio > 100 else "Potential liquidity risk"}.
            """)
            
            # Expander for raw data
            with st.expander("Show Raw Data"):
                st.json(data)

else:
    st.info("Input a ticker code and click Analyze to start.")
