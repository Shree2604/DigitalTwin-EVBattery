import streamlit as st
import firebase_admin
from firebase_admin import credentials, db
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import numpy as np
import time

# Page configuration
st.set_page_config(
    page_title="EV Battery Digital Twin",
    page_icon="🔋",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 48px;
        font-weight: bold;
        text-align: center;
        color: #1f77b4;
        margin-bottom: 20px;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 10px;
        color: white;
        text-align: center;
    }
    .status-excellent { color: #00ff00; font-weight: bold; }
    .status-good { color: #7fff00; font-weight: bold; }
    .status-fair { color: #ffff00; font-weight: bold; }
    .status-poor { color: #ff8c00; font-weight: bold; }
    .status-critical { color: #ff0000; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# Initialize Firebase
@st.cache_resource
def init_firebase():
    """Initialize Firebase connection"""
    try:
        if not firebase_admin._apps:
            cred = credentials.Certificate("digitaltwin-evbattery-firebase-adminsdk-fbsvc-c087b8aebb.json")
            firebase_admin.initialize_app(cred, {
                'databaseURL': 'https://digitaltwin-evbattery-default-rtdb.firebaseio.com/'
            })
        return True
    except Exception as e:
        st.error(f"Firebase initialization error: {e}")
        return False

def get_health_color(rul, soh):
    """Get color based on RUL and SoH"""
    if rul is None:
        return '#808080', 'unknown'
    
    if rul > 15 and soh > 80:
        return '#00ff00', 'excellent'  # Bright green
    elif rul > 10 and soh > 60:
        return '#7fff00', 'good'  # Chartreuse
    elif rul > 5 and soh > 40:
        return '#ffff00', 'fair'  # Yellow
    elif rul > 3:
        return '#ff8c00', 'poor'  # Dark orange
    else:
        return '#ff0000', 'critical'  # Red

def create_3d_battery(rul, soh, voltage):
    """Create 3D battery visualization"""
    color, status = get_health_color(rul, soh)
    
    # Battery dimensions
    battery_height = 10
    battery_width = 4
    battery_depth = 2
    
    # Fill level based on SoC
    fill_level = min(voltage / 400 * 10, 10)  # Normalize to battery height
    
    # Create battery shell (outline)
    x_shell = [0, battery_width, battery_width, 0, 0,
               0, battery_width, battery_width, 0, 0]
    y_shell = [0, 0, battery_depth, battery_depth, 0,
               0, 0, battery_depth, battery_depth, 0]
    z_shell = [0, 0, 0, 0, 0,
               battery_height, battery_height, battery_height, battery_height, battery_height]
    
    # Create mesh for battery fill
    n_points = 20
    theta = np.linspace(0, 2*np.pi, n_points)
    
    x_cylinder = []
    y_cylinder = []
    z_cylinder = []
    
    for i in range(n_points):
        x_cylinder.append(battery_width/2 + (battery_width/2 - 0.3) * np.cos(theta[i]))
        y_cylinder.append(battery_depth/2 + (battery_depth/2 - 0.3) * np.sin(theta[i]))
        z_cylinder.append(0.2)
        
    for i in range(n_points):
        x_cylinder.append(battery_width/2 + (battery_width/2 - 0.3) * np.cos(theta[i]))
        y_cylinder.append(battery_depth/2 + (battery_depth/2 - 0.3) * np.sin(theta[i]))
        z_cylinder.append(fill_level)
    
    # Create figure
    fig = go.Figure()
    
    # Add battery outline
    fig.add_trace(go.Scatter3d(
        x=x_shell, y=y_shell, z=z_shell,
        mode='lines',
        line=dict(color='black', width=4),
        name='Battery Shell',
        showlegend=False
    ))
    
    # Add vertical edges
    for i in range(4):
        fig.add_trace(go.Scatter3d(
            x=[x_shell[i], x_shell[i+5]],
            y=[y_shell[i], y_shell[i+5]],
            z=[0, battery_height],
            mode='lines',
            line=dict(color='black', width=4),
            showlegend=False
        ))
    
    # Add battery fill (3D mesh)
    fig.add_trace(go.Mesh3d(
        x=x_cylinder,
        y=y_cylinder,
        z=z_cylinder,
        color=color,
        opacity=0.8,
        name=f'Charge Level - {status.upper()}',
        showlegend=True
    ))
    
    # Add terminal (positive)
    terminal_x = [battery_width/2 - 0.5, battery_width/2 + 0.5, battery_width/2 + 0.5, battery_width/2 - 0.5, battery_width/2 - 0.5]
    terminal_y = [battery_depth/2 - 0.3, battery_depth/2 - 0.3, battery_depth/2 + 0.3, battery_depth/2 + 0.3, battery_depth/2 - 0.3]
    terminal_z = [battery_height, battery_height, battery_height, battery_height, battery_height]
    
    fig.add_trace(go.Scatter3d(
        x=terminal_x, y=terminal_y, z=terminal_z + [battery_height + 0.5]*5,
        mode='lines',
        line=dict(color='gold', width=6),
        name='Terminal',
        showlegend=False
    ))
    
    # Update layout
    fig.update_layout(
        scene=dict(
            xaxis=dict(showgrid=False, showticklabels=False, title=''),
            yaxis=dict(showgrid=False, showticklabels=False, title=''),
            zaxis=dict(showgrid=False, showticklabels=False, title=''),
            bgcolor='rgba(0,0,0,0)',
            camera=dict(
                eye=dict(x=1.5, y=1.5, z=1.2)
            )
        ),
        showlegend=True,
        legend=dict(x=0.7, y=0.9),
        margin=dict(l=0, r=0, t=30, b=0),
        height=400,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        title=dict(
            text=f"Battery Health: {status.upper()}",
            x=0.5,
            xanchor='center',
            font=dict(size=20, color=color)
        )
    )
    
    return fig

def create_3d_car(color, speed):
    """Create 3D car model"""
    fig = go.Figure()
    
    # Car body (main chassis)
    car_length = 8
    car_width = 4
    car_height = 2.5
    
    # Bottom chassis
    x_chassis = [0, car_length, car_length, 0, 0,
                 0, car_length, car_length, 0, 0]
    y_chassis = [0, 0, car_width, car_width, 0,
                 0, 0, car_width, car_width, 0]
    z_chassis = [0, 0, 0, 0, 0,
                 car_height, car_height, car_height, car_height, car_height]
    
    # Add car body
    fig.add_trace(go.Mesh3d(
        x=[0, car_length, car_length, 0, 0, car_length, car_length, 0],
        y=[0.5, 0.5, car_width-0.5, car_width-0.5, 0.5, 0.5, car_width-0.5, car_width-0.5],
        z=[0, 0, 0, 0, car_height, car_height, car_height, car_height],
        i=[0,0,0,0,4,4,6,6,4,0,3,2],
        j=[1,2,3,4,5,6,5,2,0,1,6,3],
        k=[2,3,4,5,6,7,1,1,5,5,7,7],
        color=color,
        opacity=0.9,
        name='Car Body'
    ))
    
    # Car cabin (top part)
    cabin_start = 2.5
    cabin_end = 6
    cabin_height_start = car_height
    cabin_height_end = car_height + 1.5
    
    fig.add_trace(go.Mesh3d(
        x=[cabin_start, cabin_end, cabin_end, cabin_start, cabin_start, cabin_end, cabin_end, cabin_start],
        y=[0.8, 0.8, car_width-0.8, car_width-0.8, 0.8, 0.8, car_width-0.8, car_width-0.8],
        z=[cabin_height_start, cabin_height_start, cabin_height_start, cabin_height_start,
           cabin_height_end, cabin_height_end, cabin_height_end, cabin_height_end],
        i=[0,0,0,0,4,4,6,6,4,0,3,2],
        j=[1,2,3,4,5,6,5,2,0,1,6,3],
        k=[2,3,4,5,6,7,1,1,5,5,7,7],
        color='#4A90E2',
        opacity=0.7,
        name='Cabin'
    ))
    
    # Wheels (4 cylinders)
    wheel_radius = 0.6
    wheel_thickness = 0.4
    wheel_positions = [
        (1.5, -0.2, 0),  # Front left
        (1.5, car_width + 0.2, 0),  # Front right
        (car_length - 1.5, -0.2, 0),  # Rear left
        (car_length - 1.5, car_width + 0.2, 0)  # Rear right
    ]
    
    for wx, wy, wz in wheel_positions:
        theta = np.linspace(0, 2*np.pi, 20)
        x_wheel = wx + wheel_thickness * np.cos(theta) / 2
        y_wheel = np.ones_like(theta) * wy
        z_wheel = wz + wheel_radius + wheel_radius * np.sin(theta)
        
        fig.add_trace(go.Scatter3d(
            x=x_wheel, y=y_wheel, z=z_wheel,
            mode='lines',
            line=dict(color='black', width=8),
            showlegend=False
        ))
    
    # Headlights
    fig.add_trace(go.Scatter3d(
        x=[0.1, 0.1], y=[0.8, car_width-0.8], z=[car_height*0.7, car_height*0.7],
        mode='markers',
        marker=dict(size=10, color='yellow'),
        name='Headlights',
        showlegend=False
    ))
    
    fig.update_layout(
        scene=dict(
            xaxis=dict(showgrid=False, showticklabels=False, title=''),
            yaxis=dict(showgrid=False, showticklabels=False, title=''),
            zaxis=dict(showgrid=False, showticklabels=False, title=''),
            bgcolor='rgba(240,240,240,0.5)',
            camera=dict(eye=dict(x=1.8, y=1.8, z=1.2))
        ),
        showlegend=False,
        margin=dict(l=0, r=0, t=30, b=0),
        height=400,
        title=dict(
            text=f"EV Car - Speed: {speed:.1f} km/h",
            x=0.5,
            xanchor='center',
            font=dict(size=20, color=color)
        )
    )
    
    return fig

def create_3d_bike(color, speed):
    """Create 3D bike/motorcycle model"""
    fig = go.Figure()
    
    # Bike frame
    bike_length = 6
    bike_height = 3
    
    # Main frame (simplified)
    frame_x = [1, 1.5, 3, 4.5, 5, 4.5, 3, 1.5, 1]
    frame_y = [2, 2, 2, 2, 2, 2, 2, 2, 2]
    frame_z = [1, 2.5, 2.8, 2.5, 1.2, 1.2, 1, 1, 1]
    
    fig.add_trace(go.Scatter3d(
        x=frame_x, y=frame_y, z=frame_z,
        mode='lines',
        line=dict(color=color, width=10),
        name='Frame',
        showlegend=False
    ))
    
    # Seat
    seat_x = [2.5, 3.5, 3.5, 2.5, 2.5]
    seat_y = [1.5, 1.5, 2.5, 2.5, 1.5]
    seat_z = [2.8, 2.8, 2.8, 2.8, 2.8]
    
    fig.add_trace(go.Mesh3d(
        x=[2.5, 3.5, 3.5, 2.5, 2.5, 3.5, 3.5, 2.5],
        y=[1.5, 1.5, 2.5, 2.5, 1.5, 1.5, 2.5, 2.5],
        z=[2.7, 2.7, 2.7, 2.7, 2.9, 2.9, 2.9, 2.9],
        i=[0,0,0,0,4,4,6,6],
        j=[1,2,3,4,5,6,5,2],
        k=[2,3,4,5,6,7,1,1],
        color='#2C3E50',
        opacity=0.9,
        name='Seat'
    ))
    
    # Wheels (2 circles)
    wheel_radius = 1
    wheel_positions = [(1, 2, 0), (5, 2, 0)]  # Front and rear wheels
    
    for wx, wy, wz in wheel_positions:
        theta = np.linspace(0, 2*np.pi, 30)
        x_wheel = np.ones_like(theta) * wx
        y_wheel = wy + wheel_radius * np.cos(theta) * 0.3
        z_wheel = wz + wheel_radius + wheel_radius * np.sin(theta)
        
        fig.add_trace(go.Scatter3d(
            x=x_wheel, y=y_wheel, z=z_wheel,
            mode='lines',
            line=dict(color='black', width=10),
            showlegend=False
        ))
        
        # Spokes
        for i in range(8):
            angle = i * np.pi / 4
            spoke_y = wy + wheel_radius * np.cos(angle) * 0.3
            spoke_z = wz + wheel_radius + wheel_radius * np.sin(angle)
            fig.add_trace(go.Scatter3d(
                x=[wx, wx], y=[wy, spoke_y], z=[wz + wheel_radius, spoke_z],
                mode='lines',
                line=dict(color='gray', width=2),
                showlegend=False
            ))
    
    # Handlebars
    handlebar_x = [0.8, 1.2, 1.2, 0.8]
    handlebar_y = [1.2, 1.2, 2.8, 2.8]
    handlebar_z = [2.5, 2.5, 2.5, 2.5]
    
    fig.add_trace(go.Scatter3d(
        x=handlebar_x, y=handlebar_y, z=handlebar_z,
        mode='lines',
        line=dict(color='#34495E', width=8),
        showlegend=False
    ))
    
    # Headlight
    fig.add_trace(go.Scatter3d(
        x=[0.5], y=[2], z=[2],
        mode='markers',
        marker=dict(size=15, color='yellow', symbol='diamond'),
        name='Headlight',
        showlegend=False
    ))
    
    # Battery pack (under seat)
    fig.add_trace(go.Mesh3d(
        x=[2.2, 3.8, 3.8, 2.2, 2.2, 3.8, 3.8, 2.2],
        y=[1.7, 1.7, 2.3, 2.3, 1.7, 1.7, 2.3, 2.3],
        z=[1.5, 1.5, 1.5, 1.5, 2.3, 2.3, 2.3, 2.3],
        i=[0,0,0,0,4,4,6,6],
        j=[1,2,3,4,5,6,5,2],
        k=[2,3,4,5,6,7,1,1],
        color='#27AE60',
        opacity=0.7,
        name='Battery Pack'
    ))
    
    fig.update_layout(
        scene=dict(
            xaxis=dict(showgrid=False, showticklabels=False, title=''),
            yaxis=dict(showgrid=False, showticklabels=False, title=''),
            zaxis=dict(showgrid=False, showticklabels=False, title=''),
            bgcolor='rgba(240,240,240,0.5)',
            camera=dict(eye=dict(x=1.5, y=-1.8, z=1.2))
        ),
        showlegend=False,
        margin=dict(l=0, r=0, t=30, b=0),
        height=400,
        title=dict(
            text=f"EV Bike - Speed: {speed:.1f} km/h",
            x=0.5,
            xanchor='center',
            font=dict(size=20, color=color)
        )
    )
    
    return fig

def fetch_latest_data():
    """Fetch latest data from Firebase"""
    try:
        ref = db.reference('ev_battery_data/latest')
        data = ref.get()
        return data
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        return None

def fetch_historical_data(limit=100):
    """Fetch historical data from Firebase"""
    try:
        ref = db.reference('ev_battery_data')
        data = ref.order_by_key().limit_to_last(limit).get()
        if data:
            df = pd.DataFrame.from_dict(data, orient='index')
            return df
        return None
    except Exception as e:
        st.error(f"Error fetching historical data: {e}")
        return None

def create_gauge(value, title, max_value=100, color='blue'):
    """Create gauge chart"""
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=value,
        title={'text': title, 'font': {'size': 20}},
        delta={'reference': max_value * 0.8},
        gauge={
            'axis': {'range': [0, max_value]},
            'bar': {'color': color},
            'steps': [
                {'range': [0, max_value * 0.33], 'color': "lightgray"},
                {'range': [max_value * 0.33, max_value * 0.66], 'color': "gray"}
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': max_value * 0.9
            }
        }
    ))
    
    fig.update_layout(height=250, margin=dict(l=20, r=20, t=50, b=20))
    return fig

def create_time_series(df, column, title):
    """Create time series chart"""
    fig = px.line(df, x='upload_timestamp', y=column, title=title)
    fig.update_traces(line_color='#1f77b4', line_width=2)
    fig.update_layout(
        xaxis_title="Time",
        yaxis_title=title,
        hovermode='x unified',
        height=300
    )
    return fig

def main():
    """Main dashboard function"""
    
    # Header
    st.markdown('<h1 class="main-header">🔋 EV Battery Digital Twin Dashboard</h1>', unsafe_allow_html=True)
    
    # Initialize Firebase
    if not init_firebase():
        st.stop()
    
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Dashboard Controls")
        auto_refresh = st.checkbox("Auto Refresh", value=True)
        refresh_interval = st.slider("Refresh Interval (seconds)", 1, 30, 5)
        
        st.divider()
        st.header("📊 View Options")
        show_3d = st.checkbox("3D Battery View", value=True)
        show_gauges = st.checkbox("Gauge Meters", value=True)
        show_charts = st.checkbox("Time Series Charts", value=True)
        show_alerts = st.checkbox("Alert System", value=True)
        
        st.divider()
        if st.button("🔄 Manual Refresh"):
            st.rerun()
    
    # Fetch latest data
    latest_data = fetch_latest_data()
    
    if latest_data is None:
        st.warning("⏳ Waiting for data... Please ensure the Python subscriber is running.")
        st.stop()
    
    # Extract values
    battery = latest_data.get('battery', {})
    motor = latest_data.get('motor', {})
    vehicle = latest_data.get('vehicle', {})
    environment = latest_data.get('environment', {})
    rul_data = latest_data.get('rul_prediction', {})
    
    soc = battery.get('soc', 0)
    soh = battery.get('soh', 0)
    voltage = battery.get('voltage', 0)
    current = battery.get('current', 0)
    temperature = battery.get('temperature', 0)
    
    rul = rul_data.get('value', None)
    health_status = rul_data.get('health_status', 'unknown')
    stats = rul_data.get('statistics', {})
    
    # Top metrics row
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("🔋 State of Charge", f"{soc:.1f}%", f"{soc - 80:.1f}%")
    
    with col2:
        st.metric("💚 State of Health", f"{soh:.1f}%", f"{soh - 90:.1f}%")
    
    with col3:
        if rul is not None:
            st.metric("⏰ RUL Prediction", f"{rul:.0f} cycles", 
                     delta=f"{stats.get('mean_rul', rul) - rul:.0f}")
        else:
            st.metric("⏰ RUL Prediction", "Buffering...", delta=None)
    
    with col4:
        color, status = get_health_color(rul, soh)
        st.markdown(f"### Health Status")
        st.markdown(f'<p class="status-{status}">{status.upper()}</p>', unsafe_allow_html=True)
    
    with col5:
        st.metric("🌡️ Temperature", f"{temperature:.1f}°C", 
                 delta=f"{temperature - 25:.1f}°C")
    
    st.divider()
    
    # Main content area - 3D Models
    if show_3d:
        st.subheader("🎯 3D Vehicle & Battery Visualization")
        
        # Three 3D models in a row
        model_col1, model_col2, model_col3 = st.columns(3)
        
        with model_col1:
            st.markdown("### 🔋 Battery Pack")
            if rul is not None:
                fig_battery = create_3d_battery(rul, soh, voltage)
                st.plotly_chart(fig_battery, use_container_width=True)
            else:
                st.info("⏳ Collecting data...")
        
        with model_col2:
            st.markdown("### 🚗 EV Car")
            vehicle_color, _ = get_health_color(rul, soh)
            fig_car = create_3d_car(vehicle_color, vehicle.get('driving_speed', 0))
            st.plotly_chart(fig_car, use_container_width=True)
        
        with model_col3:
            st.markdown("### 🏍️ EV Bike")
            fig_bike = create_3d_bike(vehicle_color, vehicle.get('driving_speed', 0))
            st.plotly_chart(fig_bike, use_container_width=True)
        
        st.divider()
        
        # Details section below 3D models
        col_details1, col_details2, col_details3 = st.columns(3)
        
        with col_details1:
            st.subheader("📋 Battery Details")
            st.write(f"**Voltage:** {voltage:.2f} V")
            st.write(f"**Current:** {current:.2f} A")
            st.write(f"**Temperature:** {temperature:.1f} °C")
            st.write(f"**Charge Cycles:** {battery.get('charge_cycles', 0):.0f}")
            
            st.divider()
            
            st.subheader("🚗 Vehicle Metrics")
            st.write(f"**Speed:** {vehicle.get('driving_speed', 0):.1f} km/h")
            st.write(f"**Power:** {vehicle.get('power_consumption', 0):.1f} kW")
            st.write(f"**Distance:** {vehicle.get('distance_traveled', 0):.1f} km")
            
            st.divider()
            
            if stats:
                st.subheader("📈 RUL Statistics")
                st.write(f"**Current:** {stats.get('current_rul', 0):.1f}")
                st.write(f"**Mean:** {stats.get('mean_rul', 0):.1f}")
                st.write(f"**Trend:** {stats.get('trend', 'N/A').upper()}")
    
    st.divider()
    
    # Gauges
    if show_gauges:
        st.subheader("📊 Real-Time Gauges")
        gauge_col1, gauge_col2, gauge_col3, gauge_col4 = st.columns(4)
        
        with gauge_col1:
            fig_soc = create_gauge(soc, "SoC (%)", 100, 'green')
            st.plotly_chart(fig_soc, use_container_width=True)
        
        with gauge_col2:
            fig_soh = create_gauge(soh, "SoH (%)", 100, 'blue')
            st.plotly_chart(fig_soh, use_container_width=True)
        
        with gauge_col3:
            fig_temp = create_gauge(temperature, "Temp (°C)", 100, 'red')
            st.plotly_chart(fig_temp, use_container_width=True)
        
        with gauge_col4:
            fig_speed = create_gauge(vehicle.get('driving_speed', 0), "Speed (km/h)", 200, 'purple')
            st.plotly_chart(fig_speed, use_container_width=True)
    
    st.divider()
    
    # Time series charts
    if show_charts:
        st.subheader("📈 Historical Trends")
        hist_data = fetch_historical_data(limit=50)
        
        if hist_data is not None and not hist_data.empty:
            # Parse nested data
            hist_data['soc'] = hist_data['battery'].apply(lambda x: x.get('soc', 0) if isinstance(x, dict) else 0)
            hist_data['soh'] = hist_data['battery'].apply(lambda x: x.get('soh', 0) if isinstance(x, dict) else 0)
            hist_data['rul'] = hist_data['rul_prediction'].apply(lambda x: x.get('value', None) if isinstance(x, dict) else None)
            hist_data['temperature'] = hist_data['battery'].apply(lambda x: x.get('temperature', 0) if isinstance(x, dict) else 0)
            
            chart_col1, chart_col2 = st.columns(2)
            
            with chart_col1:
                fig_soc_trend = create_time_series(hist_data, 'soc', 'State of Charge (%)')
                st.plotly_chart(fig_soc_trend, use_container_width=True)
            
            with chart_col2:
                fig_rul_trend = create_time_series(hist_data.dropna(subset=['rul']), 'rul', 'RUL Prediction')
                st.plotly_chart(fig_rul_trend, use_container_width=True)
        else:
            st.info("📊 Historical data will appear here once more data is collected.")
    
    st.divider()
    
    # Alerts
    if show_alerts:
        st.subheader("🚨 System Alerts")
        
        try:
            alerts_ref = db.reference('alerts')
            alerts = alerts_ref.order_by_key().limit_to_last(5).get()
            
            if alerts:
                for alert_id, alert in reversed(list(alerts.items())):
                    severity = alert.get('severity', 'info')
                    if severity == 'critical':
                        st.error(f"🔴 **CRITICAL:** {alert.get('message', 'N/A')} - {alert.get('timestamp', 'N/A')}")
                    else:
                        st.warning(f"⚠️ **WARNING:** {alert.get('message', 'N/A')} - {alert.get('timestamp', 'N/A')}")
            else:
                st.success("✅ No alerts - System operating normally")
        except:
            st.info("No alerts available")
    
    # Auto refresh
    if auto_refresh:
        time.sleep(refresh_interval)
        st.rerun()

if __name__ == "__main__":
    main()