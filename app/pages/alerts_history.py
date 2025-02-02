import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import plotly.graph_objects as go
import influxdb_client

st.set_page_config(page_title="Alerts History", page_icon="⚠️", layout="wide")

def get_alerts_history():
    """Retrieve alerts history from InfluxDB"""
    client = influxdb_client.InfluxDBClient(
        url=st.secrets["INFLUXDB_URL"],
        token=st.secrets["INFLUXDB_TOKEN"],
        org=st.secrets["INFLUXDB_ORG"]
    )
    
    query_api = client.query_api()
    
    # Query last 24 hours of alerts
    query = '''
    from(bucket: "system_metrics")
        |> range(start: -24h)
        |> filter(fn: (r) => r["_measurement"] == "system_metrics")
        |> filter(fn: (r) => r["_field"] == "cpu" or r["_field"] == "memory")
    '''
    
    result = query_api.query(query=query)
    
    alerts = []
    for table in result:
        for record in table.records:
            if (record.get_field() == "cpu" and record.get_value() > 90) or \
               (record.get_field() == "memory" and record.get_value() > 85):
                alerts.append({
                    'timestamp': record.get_time(),
                    'metric': record.get_field(),
                    'value': record.get_value(),
                    'host': record.values.get('host', 'unknown')
                })
    
    return pd.DataFrame(alerts)

def main():
    st.title("⚠️ Alerts History")
    
    # Date range selector
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input(
            "Start Date",
            datetime.now().date() - timedelta(days=7)
        )
    with col2:
        end_date = st.date_input(
            "End Date",
            datetime.now().date()
        )
    
    # Get alerts history
    df = get_alerts_history()
    
    if df.empty:
        st.info("No alerts found in the selected time range")
        return
    
    # Filter by date range
    df['date'] = pd.to_datetime(df['timestamp']).dt.date
    df_filtered = df[(df['date'] >= start_date) & (df['date'] <= end_date)]
    
    # Alerts Summary
    st.header("Alerts Summary")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Alerts", len(df_filtered))
    with col2:
        st.metric("CPU Alerts", len(df_filtered[df_filtered['metric'] == 'cpu']))
    with col3:
        st.metric("Memory Alerts", len(df_filtered[df_filtered['metric'] == 'memory']))
    
    # Alerts Timeline
    st.header("Alerts Timeline")
    fig = go.Figure()
    
    for metric in df_filtered['metric'].unique():
        metric_df = df_filtered[df_filtered['metric'] == metric]
        fig.add_trace(go.Scatter(
            x=metric_df['timestamp'],
            y=metric_df['value'],
            mode='markers',
            name=metric.upper(),
            hovertemplate="Time: %{x}<br>Value: %{y:.2f}%<br>Host: %{text}<extra></extra>",
            text=metric_df['host']
        ))
    
    fig.update_layout(
        height=400,
        yaxis_title="Value (%)",
        xaxis_title="Time"
    )
    st.plotly_chart(fig, use_container_width=True)
    
    # Detailed Alerts Table
    st.header("Detailed Alerts")
    st.dataframe(
        df_filtered.sort_values('timestamp', ascending=False),
        use_container_width=True,
        hide_index=True
    )
    
    # Export option
    if st.button("📥 Export Alerts"):
        csv = df_filtered.to_csv(index=False)
        st.download_button(
            "Download CSV",
            csv,
            "alerts_history.csv",
            "text/csv",
            key='download-csv'
        )

if __name__ == "__main__":
    main()