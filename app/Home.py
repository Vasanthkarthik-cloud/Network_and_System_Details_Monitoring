import streamlit as st
import psutil
import time
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import numpy as np
import socket
import logging
import platform
import cpuinfo
from collections import defaultdict
import influxdb_client
from influxdb_client.client.write_api import SYNCHRONOUS
import warnings
import jwt
from st_pages import Page  # Changed from show_pages_from_config
from functools import lru_cache

# Suppress unnecessary warnings
warnings.filterwarnings('ignore')

# Constants
HISTORY_SIZE = 500
REFRESH_INTERVALS = [1, 2, 5, 10, 30]
DEFAULT_INTERFACE = 'eth0'

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EnhancedSystemMonitor:
    def __init__(self):
        self.cpu_info = cpuinfo.get_cpu_info()
        self.os_info = {
            'system': platform.system(),
            'release': platform.release(),
            'version': platform.version()
        }
        
    @lru_cache(maxsize=1)
    def get_system_info(self):
        """Get cached system information"""
        return {
            'cpu_name': self.cpu_info.get('brand_raw', 'Unknown CPU'),
            'cores_physical': psutil.cpu_count(logical=False),
            'cores_logical': psutil.cpu_count(logical=True),
            'os_version': f"{self.os_info['system']} {self.os_info['release']}"
        }

class AdvancedNetworkMonitor:
    def __init__(self):
        self.historical_data = []
        self.max_history_size = HISTORY_SIZE
        self.interface_stats = defaultdict(list)
        
    def get_network_stats(self, interfaces: list):
        """Get statistics for multiple interfaces"""
        stats = []
        for interface in interfaces:
            try:
                io = psutil.net_io_counters(pernic=True).get(interface)
                addrs = psutil.net_if_addrs().get(interface, [])
                ipv4 = next((addr.address for addr in addrs if addr.family == socket.AF_INET), 'N/A')
                ipv6 = next((addr.address for addr in addrs if addr.family == socket.AF_INET6), 'N/A')
                mac = next((addr.address for addr in addrs if addr.family == psutil.AF_LINK), 'N/A')
                
                stat = {
                    'interface': interface,
                    'timestamp': datetime.now(),
                    'bytes_sent': io.bytes_sent,
                    'bytes_recv': io.bytes_recv,
                    'errors_in': io.errin,
                    'errors_out': io.errout,
                    'dropped_in': io.dropin,
                    'dropped_out': io.dropout,
                    'ipv4': ipv4,
                    'ipv6': ipv6,
                    'mac': mac,
                    'active_connections': len(psutil.net_connections())
                }
                stats.append(stat)
                self._update_interface_history(interface, stat)
            except Exception as e:
                logger.error(f"Error getting stats for {interface}: {str(e)}")
        return stats
    
    def _update_interface_history(self, interface: str, stat: dict):
        """Maintain historical data for each interface"""
        if len(self.interface_stats[interface]) >= self.max_history_size:
            self.interface_stats[interface].pop(0)
        self.interface_stats[interface].append(stat)

class DataStorage:
    def __init__(self):
        influx_url = st.secrets["INFLUXDB"]["URL"]
        influx_token = st.secrets["INFLUXDB"]["TOKEN"]
        influx_org = st.secrets["INFLUXDB"]["ORG"]
        influx_bucket = st.secrets["INFLUXDB"]["BUCKET"]

        self.influx_client = influxdb_client.InfluxDBClient(
            url=influx_url,
            token=influx_token,
            org=influx_org
        )
        self.write_api = self.influx_client.write_api(write_options=SYNCHRONOUS)
        self.influx_bucket = influx_bucket
        
    def write_metrics(self, measurement: str, fields: dict, tags: dict = None):
        """Write metrics to InfluxDB"""
        point = influxdb_client.Point(measurement)
        for key, value in fields.items():
            point.field(key, value)
        if tags:
            for key, value in tags.items():
                point.tag(key, value)
        self.write_api.write(
            bucket=self.influx_bucket,
            org=self.influx_client.org,
            record=point
        )

def setup_authentication():
    """Set up JWT-based authentication"""
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
        
    if not st.session_state.authenticated:
        with st.form("auth"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            if st.form_submit_button("Login"):
                if (username == st.secrets["ADMIN"]["USER"] and 
                    password == st.secrets["ADMIN"]["PASS"]):
                    st.session_state.authenticated = True
                    st.rerun()
                else:
                    st.error("Invalid credentials")
        st.stop()

def create_alert_system():
    """Create alert configuration interface"""
    with st.expander("⚡ Alert Configuration"):
        col1, col2 = st.columns(2)
        with col1:
            cpu_threshold = st.slider("CPU Alert Threshold (%)", 0, 100, 90)
            memory_threshold = st.slider("Memory Alert Threshold (%)", 0, 100, 85)
        with col2:
            network_in_threshold = st.number_input("Network In Alert (MB/s)", 0, 1000, 100)
            network_out_threshold = st.number_input("Network Out Alert (MB/s)", 0, 1000, 100)
            
        return {
            'cpu': cpu_threshold,
            'memory': memory_threshold,
            'network_in': network_in_threshold * 1024**2,
            'network_out': network_out_threshold * 1024**2
        }

def check_alerts(stats: dict, thresholds: dict):
    """Check metrics against thresholds and trigger alerts"""
    alerts = []
    if stats['cpu_percent'] > thresholds['cpu']:
        alerts.append(f"High CPU usage: {stats['cpu_percent']}%")
    if stats['memory_percent'] > thresholds['memory']:
        alerts.append(f"High Memory usage: {stats['memory_percent']}%")
    if stats['bytes_recv'] > thresholds['network_in']:
        alerts.append(f"High Network In: {format_bytes(stats['bytes_recv'])}")
    if stats['bytes_sent'] > thresholds['network_out']:
        alerts.append(f"High Network Out: {format_bytes(stats['bytes_sent'])}")
    
    if alerts:
        with st.container():
            st.error("## Active Alerts")
            for alert in alerts:
                st.write(f"⚠️ {alert}")

def format_bytes(size: float) -> str:
    """Format bytes to human-readable format"""
    power = 2**10
    n = 0
    units = {0: 'B', 1: 'KB', 2: 'MB', 3: 'GB', 4: 'TB'}
    while size > power and n < len(units)-1:
        size /= power
        n += 1
    return f"{size:.2f} {units[n]}"

def render_network_metrics(network_monitor, interfaces):
    """Render enhanced network metrics visualization with data rates"""
    st.subheader("Network Metrics")
    
    for interface in interfaces:
        stats = network_monitor.interface_stats[interface]
        if stats:
            with st.expander(f"Interface: {interface}", expanded=True):
                df = pd.DataFrame(stats)
                
                # Convert bytes to megabytes and calculate rates
                df['MB_sent'] = df['bytes_sent'] / (1024 * 1024)
                df['MB_recv'] = df['bytes_recv'] / (1024 * 1024)
                
                # Calculate data rates (MB/s)
                df['send_rate'] = df['MB_sent'].diff() / df['timestamp'].diff().dt.total_seconds()
                df['recv_rate'] = df['MB_recv'].diff() / df['timestamp'].diff().dt.total_seconds()
                
                # Create two subplots: one for cumulative data, one for rates
                fig = make_subplots(rows=2, cols=1, 
                                  subplot_titles=(f"Cumulative Traffic (MB)", 
                                                f"Data Rate (MB/s)"),
                                  vertical_spacing=0.15)
                
                # Cumulative traffic plot
                fig.add_trace(
                    go.Scatter(x=df['timestamp'], 
                              y=df['MB_sent'],
                              name='Data Sent',
                              fill='tozeroy',
                              line=dict(color='rgba(0, 150, 255, 0.8)')),
                    row=1, col=1
                )
                
                fig.add_trace(
                    go.Scatter(x=df['timestamp'], 
                              y=df['MB_recv'],
                              name='Data Received',
                              fill='tozeroy',
                              line=dict(color='rgba(255, 102, 0, 0.8)')),
                    row=1, col=1
                )
                
                # Data rate plot
                fig.add_trace(
                    go.Scatter(x=df['timestamp'],
                              y=df['send_rate'],
                              name='Send Rate',
                              line=dict(color='rgba(0, 150, 255, 0.8)')),
                    row=2, col=1
                )
                
                fig.add_trace(
                    go.Scatter(x=df['timestamp'],
                              y=df['recv_rate'],
                              name='Receive Rate',
                              line=dict(color='rgba(255, 102, 0, 0.8)')),
                    row=2, col=1
                )
                
                # Update layout for better visualization
                fig.update_layout(
                    height=700,
                    showlegend=True,
                    legend=dict(
                        yanchor="top",
                        y=0.99,
                        xanchor="left",
                        x=0.01
                    ),
                    hovermode='x unified',
                    margin=dict(l=20, r=20, t=60, b=20)
                )
                
                # Update axes labels and styling
                fig.update_xaxes(title_text="Time", row=2, col=1)
                fig.update_xaxes(showticklabels=True, row=1, col=1)
                fig.update_yaxes(title_text="MB", row=1, col=1)
                fig.update_yaxes(title_text="MB/s", row=2, col=1)
                
                # Add hover template
                fig.update_traces(
                    hovertemplate="<b>Time</b>: %{x}<br>" +
                                "<b>Value</b>: %{y:.2f}<br>"
                )
                
                # Display current stats
                col1, col2 = st.columns(2)
                with col1:
                    st.metric(
                        "Total Data Sent",
                        f"{df['MB_sent'].iloc[-1]:.2f} MB",
                        f"{df['send_rate'].iloc[-1]:.2f} MB/s"
                    )
                with col2:
                    st.metric(
                        "Total Data Received",
                        f"{df['MB_recv'].iloc[-1]:.2f} MB",
                        f"{df['recv_rate'].iloc[-1]:.2f} MB/s"
                    )
                
                st.plotly_chart(fig, use_container_width=True)

def render_system_metrics(system_monitor, memory):
    """Render system metrics visualization"""
    st.subheader("System Metrics")
    col1, col2 = st.columns(2)
    
    with col1:
        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=psutil.cpu_percent(),
            title={'text': "CPU Usage"},
            gauge={'axis': {'range': [0, 100]}}
        ))
        st.plotly_chart(fig, use_container_width=True)
        
    with col2:
        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=memory.percent,
            title={'text': "Memory Usage"},
            gauge={'axis': {'range': [0, 100]}}
        ))
        st.plotly_chart(fig, use_container_width=True)

def main():
    # Set up page configuration
    st.set_page_config(
        page_title="Enterprise System Monitor",
        page_icon="📊",
        layout="wide"
    )
    
    # Add page navigation
    # add_page_title()
    # add_indentation()  # Add indentation to the navigation
    # show_pages([
    #     Page("Home.py", "Dashboard", "🏠"),
    #     Page("pages/system_details.py", "System Details", "💻"),
    #     Page("pages/network_analysis.py", "Network Analysis", "🌐"),
    #     Page("pages/alerts_history.py", "Alerts History", "⚠️")
    # ])
    
    # Authentication
    setup_authentication()
    
    # Initialize components
    system_monitor = EnhancedSystemMonitor()
    network_monitor = AdvancedNetworkMonitor()
    data_storage = DataStorage()
    
    # Multi-interface selection
    interfaces = list(psutil.net_io_counters(pernic=True).keys())
    selected_interfaces = st.multiselect(
        "Select Network Interfaces",
        interfaces,
        default=[DEFAULT_INTERFACE] if DEFAULT_INTERFACE in interfaces else interfaces[:1]
    )
    
    # Alert configuration
    thresholds = create_alert_system()
    
    # Dashboard layout
    with st.container():
        col1, col2, col3 = st.columns(3)
        with col1:
            refresh_rate = st.selectbox("Refresh Rate", REFRESH_INTERVALS, index=1)
        with col2:
            st.write("## System Overview")
        with col3:
            if st.button("🔄 Force Refresh"):
                st.rerun()
    
    # Main monitoring loop
    while True:
        try:
            # Collect metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            network_stats = network_monitor.get_network_stats(selected_interfaces)
            
            # Store metrics
            data_storage.write_metrics(
                measurement="system_metrics",
                fields={
                    'cpu': cpu_percent,
                    'memory': memory.percent,
                    'network_in': sum(s['bytes_recv'] for s in network_stats),
                    'network_out': sum(s['bytes_sent'] for s in network_stats)
                },
                tags={'host': socket.gethostname()}
            )
            
            # Check alerts
            check_alerts({
                'cpu_percent': cpu_percent,
                'memory_percent': memory.percent,
                'bytes_recv': sum(s['bytes_recv'] for s in network_stats),
                'bytes_sent': sum(s['bytes_sent'] for s in network_stats)
            }, thresholds)
            
            # Visualizations
            render_network_metrics(network_monitor, selected_interfaces)
            render_system_metrics(system_monitor, memory)
            
            time.sleep(refresh_rate)
            st.rerun()
            
        except Exception as e:
            logger.error(f"Monitoring error: {str(e)}")
            st.error(f"Monitoring error: {str(e)}")
            time.sleep(5)
            st.rerun()

if __name__ == "__main__":
    main()