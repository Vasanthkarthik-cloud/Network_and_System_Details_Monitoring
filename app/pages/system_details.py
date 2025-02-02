import streamlit as st
import psutil
import platform
import cpuinfo
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="System Details", page_icon="💻", layout="wide")

def get_disk_info():
    disk_info = []
    for partition in psutil.disk_partitions():
        try:
            usage = psutil.disk_usage(partition.mountpoint)
            disk_info.append({
                'Device': partition.device,
                'Mountpoint': partition.mountpoint,
                'File System': partition.fstype,
                'Total': f"{usage.total / (1024**3):.2f} GB",
                'Used': f"{usage.used / (1024**3):.2f} GB",
                'Free': f"{usage.free / (1024**3):.2f} GB",
                'Usage': f"{usage.percent}%"
            })
        except Exception:
            continue
    return disk_info

def main():
    st.title("🖥️ System Details")
    
    # CPU Information
    st.header("CPU Information")
    cpu_info = cpuinfo.get_cpu_info()
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("CPU Model", cpu_info.get('brand_raw', 'Unknown'))
        st.metric("Architecture", cpu_info.get('arch', 'Unknown'))
    with col2:
        st.metric("Physical Cores", psutil.cpu_count(logical=False))
        st.metric("Logical Cores", psutil.cpu_count(logical=True))
    with col3:
        st.metric("Current Frequency", f"{psutil.cpu_freq().current:.2f} MHz")
        st.metric("CPU Usage", f"{psutil.cpu_percent()}%")
    
    # Memory Information
    st.header("Memory Information")
    memory = psutil.virtual_memory()
    swap = psutil.swap_memory()
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("RAM")
        st.metric("Total", f"{memory.total / (1024**3):.2f} GB")
        st.metric("Available", f"{memory.available / (1024**3):.2f} GB")
        st.metric("Used", f"{memory.used / (1024**3):.2f} GB")
        st.metric("Usage", f"{memory.percent}%")
    
    with col2:
        st.subheader("Swap")
        st.metric("Total", f"{swap.total / (1024**3):.2f} GB")
        st.metric("Used", f"{swap.used / (1024**3):.2f} GB")
        st.metric("Free", f"{swap.free / (1024**3):.2f} GB")
        st.metric("Usage", f"{swap.percent}%")
    
    # Disk Information
    st.header("Disk Information")
    disk_info = get_disk_info()
    if disk_info:
        st.dataframe(
            pd.DataFrame(disk_info),
            use_container_width=True,
            hide_index=True
        )
    
    # System Information
    st.header("System Information")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Operating System", f"{platform.system()} {platform.release()}")
        st.metric("Platform", platform.platform())
    with col2:
        st.metric("Python Version", platform.python_version())
        st.metric("Machine", platform.machine())
    
    # Update timestamp
    st.sidebar.write(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    if st.sidebar.button("🔄 Refresh Data"):
        st.rerun()

if __name__ == "__main__":
    main()