import plotly.graph_objects as go
import plotly.express as px

def plot_revenue_profit(df):
    """
    Creates a multi-bar chart for Revenue, Gross Profit, EBITDA, and Net Profit.
    """
    fig = go.Figure()
    
    fig.add_trace(go.Bar(x=df['Year'], y=df['Revenue'], name='Revenue'))
    fig.add_trace(go.Bar(x=df['Year'], y=df['Gross Profit'], name='Gross Profit'))
    fig.add_trace(go.Bar(x=df['Year'], y=df['EBITDA'], name='EBITDA'))
    fig.add_trace(go.Bar(x=df['Year'], y=df['Net Profit'], name='Net Profit'))
    
    fig.update_layout(
        title='Revenue & Profit Trends',
        xaxis_title='Year',
        yaxis_title='Amount',
        barmode='group',
        template='plotly_white'
    )
    return fig

def plot_margins(df):
    """
    Creates a line chart for profitability margins.
    """
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(x=df['Year'], y=df['Gross Margin (%)'], mode='lines+markers', name='Gross Margin %'))
    fig.add_trace(go.Scatter(x=df['Year'], y=df['EBITDA Margin (%)'], mode='lines+markers', name='EBITDA Margin %'))
    fig.add_trace(go.Scatter(x=df['Year'], y=df['Net Margin (%)'], mode='lines+markers', name='Net Margin %'))
    
    fig.update_layout(
        title='Profitability Margins Trend',
        xaxis_title='Year',
        yaxis_title='Percentage (%)',
        template='plotly_white'
    )
    return fig

def plot_debt_equity(df):
    """
    Creates a stacked bar chart for Debt vs Equity structure.
    """
    fig = go.Figure()
    
    fig.add_trace(go.Bar(x=df['Year'], y=df['Total Debt'], name='Total Debt'))
    fig.add_trace(go.Bar(x=df['Year'], y=df['Equity'], name='Equity'))
    
    fig.update_layout(
        title='Capital Structure (Debt vs Equity)',
        xaxis_title='Year',
        yaxis_title='Amount',
        barmode='stack',
        template='plotly_white'
    )
    return fig

def plot_cash_flow_vs_income(df):
    """
    Compares Operating Cash Flow vs Net Income.
    """
    fig = go.Figure()
    
    fig.add_trace(go.Bar(x=df['Year'], y=df['Net Profit'], name='Net Profit'))
    fig.add_trace(go.Scatter(x=df['Year'], y=df['Operating Cash Flow'], mode='lines+markers', name='Operating Cash Flow', line=dict(color='green', width=3)))
    
    fig.update_layout(
        title='Operating Cash Flow vs Net Income',
        xaxis_title='Year',
        yaxis_title='Amount',
        template='plotly_white'
    )
    return fig
