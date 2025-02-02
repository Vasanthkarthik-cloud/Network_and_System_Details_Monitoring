import streamlit as st
import psutil
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import socket
from datetime import datetime
import time

st.set_page_config(page_title="Network Analysis", page_icon="🌐", layout="wide")

def get_connection_info():
    connections = []
    for conn in psutil.net_connections():
        try:
            connections.append({
                'Local Address': f"{conn.laddr.ip}:{conn.laddr.port}",
                'Remote Address': f"{conn.raddr.ip}:{conn.raddr.port}" if conn.raddr else "N/A",
                'Status': conn.status,
                'PID': conn.pid or "N/A"
            })
        except (AttributeError, ValueError):
            continue
    return connections

def format_bytes(bytes):
    """Format bytes to human readable format"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes < 1024:
            return f"{bytes:.2f} {unit}"
        bytes /= 1024
    return f"{bytes:.2f} TB"

def main():
    st.title("🌐 Network Analysis")
    
    # Get network interfaces
    interfaces = list(psutil.net_if_addrs().keys())
    selected_interface = st.selectbox(
        "Select Network Interface",
        interfaces,
        index=0
    )
    
    # Network Interface Details
    st.header("Interface Details")
    addrs = psutil.net_if_addrs()[selected_interface]
    
    col1, col2, col3 = st.columns(3)
    with col1:
        ipv4 = next((addr.address for addr in addrs if addr.family == socket.AF_INET), 'N/A')
        st.metric("IPv4 Address", ipv4)
    with col2:
        ipv6 = next((addr.address for addr in addrs if addr.family == socket.AF_INET6), 'N/A')
        st.metric("IPv6 Address", ipv6)
    with col3:
        mac = next((addr.address for addr in addrs if addr.family == psutil.AF_LINK), 'N/A')
        st.metric("MAC Address", mac)
    
    # Network Traffic
    st.header("Network Traffic")
    io_counters = psutil.net_io_counters(pernic=True)[selected_interface]
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Bytes Sent", format_bytes(io_counters.bytes_sent))
        st.metric("Packets Sent", format_bytes(io_counters.packets_sent))
        st.metric("Errors Out", io_counters.errout)
        st.metric("Dropped Out", io_counters.dropout)
    with col2:
        st.metric("Bytes Received", format_bytes(io_counters.bytes_recv))
        st.metric("Packets Received", format_bytes(io_counters.packets_recv))
        st.metric("Errors In", io_counters.errin)
        st.metric("Dropped In", io_counters.dropin)
    
    # Active Connections
    st.header("Active Connections")
    connections = get_connection_info()
    if connections:
        st.dataframe(
            pd.DataFrame(connections),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("No active connections found")
    
    # Auto-refresh option
    refresh_rate = st.sidebar.selectbox(
        "Refresh Rate",
        [1, 2, 5, 10, 30],
        index=2,
        help="Select how often to refresh the data (in seconds)"
    )
    
    st.sidebar.write(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    time.sleep(refresh_rate)
    st.rerun()

if __name__ == "__main__":
    main()