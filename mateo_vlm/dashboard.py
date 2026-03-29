import streamlit as st
import os
import json
from datetime import datetime

if not os.path.exists("current_target.txt"):
    with open("current_target.txt", "w") as f:
        f.write("boat")

# Read the current active target so we can pre-fill the text box with it
with open("current_target.txt", "r") as f:
    current_active_target = f.read().strip()
    if not current_active_target:
        current_active_target = "boat"

# --- UI Configuration ---
st.set_page_config(page_title="UMD1 Boat Control", layout="wide")
st.title("Autonomous Vessel Go Vroom")

# Apply a global serif font across the app.
st.markdown(
    """
    <style>
    html, body, [class*="css"], [data-testid="stAppViewContainer"], [data-testid="stSidebar"] {
        font-family: "Times New Roman", Times, serif;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# --- Sidebar ---
with st.sidebar:
    st.header("UMD1 Boat Control")
    selected_boat = st.selectbox("Select Vessel:", ["Boat 1 (Pi)"])
    
    st.success("ZMQ port success")

    st.divider()
    st.write("### Specify Target")
    
    # Text input for the new target
    new_target = st.text_input("Instruct boat to look for:", placeholder="e.g., boat, green kayak")
    
    if st.button("Update Target"):
        if new_target:
            # Write to the drop-box file
            with open("current_target.txt", "w") as f:
                f.write(new_target)
            st.success(f"Directive updated: {new_target}")
        else:
            st.warning("Please enter a target.")

# --- Main Dashboard Logic ---
# Map the UI selection to the actual folder name
folder_map = {"Boat 1 (Pi)": "data"}
target_dir = folder_map[selected_boat]

st.subheader(f"Recent Incident Reports: {selected_boat}")

# Ensure the directory exists so the app doesn't crash on first run
if not os.path.exists(target_dir):
    st.warning("No data directory found. Start the ZMQ Command Center and trigger an alert.")
else:
    # 1. Find all metadata files
    files = os.listdir(target_dir)
    meta_files = [f for f in files if f.endswith("_meta.json")]
    
    if not meta_files:
        st.info("Nothing detected yet.")
    else:
        # 2. Sort them so the newest alerts are at the top
        meta_files.sort(reverse=True)
        
        # 3. Create a nice visual container for each alert
        for meta_file in meta_files:
            # Extract the timestamp prefix (e.g., "1710000000" from "1710000000_meta.json")
            timestamp_str = meta_file.split("_")[0]
            vid_file = f"{timestamp_str}_video.mp4"
            
            meta_path = os.path.join(target_dir, meta_file)
            vid_path = os.path.join(target_dir, vid_file)
            
            # Load the JSON data
            with open(meta_path, "r") as f:
                data = json.load(f)
                
            # Convert Unix timestamp to a readable human time
            readable_time = datetime.fromtimestamp(data["timestamp"]).strftime('%Y-%m-%d %H:%M:%S')
            detected_target = data.get("current_target", "Boat").title() # Fallback to "Boat" if not present

            
            # --- Render the Alert UI ---
            # Use an expander so the screen doesn't get cluttered if you have 50 alerts
            with st.expander(f"{detected_target} Detected at {readable_time}", expanded=True):
                col1, col2 = st.columns([2, 1]) # Make video column wider than text column
                
                with col1:
                    if os.path.exists(vid_path):
                        # Natively play the mp4
                        st.video(vid_path)
                    else:
                        st.error("Video file missing!")
                        
                with col2:
                    st.write("### Incident Details")
                    st.write(f"**Description:** {data['message']}")
                    st.write(f"**Capture Framerate:** {data['fps']} FPS")
                    st.write(f"**Clip Duration:** {data['duration']} seconds")
                    
                    # You can add a button here later to "Acknowledge" or "Delete" the alert
                    if st.button("Acknowledge Alert", key=timestamp_str):
                        st.toast("Alert acknowledged and logged.")