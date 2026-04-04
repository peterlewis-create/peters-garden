import streamlit as st
import google.generativeai as genai
import base64
import json
import os
from datetime import datetime
from PIL import Image
import io
import urllib.parse

# 1. HEIC support
try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
except: pass

# 2. Database Logic
DB_FILE = "peters_garden_database.json"
CONFIG_FILE = "peters_garden_config.json"

def load_data():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r") as f:
                data = json.load(f)
                return [p for p in data if isinstance(p, dict) and p.get('name')]
        except: return []
    return []

def save_data(data):
    with open(DB_FILE, "w") as f: json.dump(data, f)

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f: return json.load(f)
    return {"api_key": ""}

def save_config(config):
    with open(CONFIG_FILE, "w") as f: json.dump(config, f)

if "garden" not in st.session_state: st.session_state.garden = load_data()
if "config" not in st.session_state: st.session_state.config = load_config()
if "view_mode" not in st.session_state: st.session_state.view_mode = "gallery"
if "selected_plant" not in st.session_state: st.session_state.selected_plant = None

st.set_page_config(page_title="Peter's Garden", layout="wide", page_icon="🌿")

# 3. ABSOLUTE HIGH-CONTRAST MOBILE STYLING
st.markdown("""
    <style>
    /* Force Pure Black Background everywhere */
    .stApp, [data-testid="stSidebar"], .stMarkdown { background-color: #000000 !important; }
    
    /* Force Pure White Text everywhere */
    p, li, h1, h2, h3, span, label, div, small, .stMarkdown { color: #FFFFFF !important; }
    
    /* FIX THE WHITE BUTTONS */
    /* This makes all buttons Black background with White text and a White border */
    button {
        background-color: #111111 !important;
        color: #FFFFFF !important;
        border: 1px solid #FFFFFF !important;
        border-radius: 8px !important;
        height: auto !important;
        padding: 10px 20px !important;
    }
    
    /* Hover effect for buttons */
    button:hover {
        background-color: #333333 !important;
        border-color: #22C55E !important;
    }

    /* Gallery Card Styling */
    .gallery-card {
        background-color: #000000;
        padding: 10px;
        border-radius: 15px;
        border: 2px solid #333333;
        text-align: center;
        margin-bottom: 30px;
    }
    
    /* Sidebar Input Boxes */
    input {
        background-color: #222222 !important;
        color: #FFFFFF !important;
        border: 1px solid #444444 !important;
    }

    /* Dashboard Boxes */
    .box { padding: 20px; border-radius: 12px; margin-bottom: 20px; border: 4px solid; background-color: #000000; }
    .box-flourish { border-color: #22C55E; }
    .box-forbidden { border-color: #EF4444; }
    .box-prune { border-color: #3B82F6; }
    .header-label { font-weight: 900; color: #FFFFFF !important; font-size: 1.3rem; text-transform: uppercase; margin-bottom: 10px; display: block; }
    
    /* iPhone Sidebar Toggle Button Visibility */
    [data-testid="stSidebarCollapsedControl"] {
        background-color: #22C55E !important;
        color: black !important;
        border-radius: 5px;
    }
    </style>
    """, unsafe_allow_html=True)

# Helper functions
def get_any_image(plant):
    if plant.get('image'): return plant['image']
    if 'history' in plant and len(plant['history']) > 0: return plant['history'][-1]['image']
    return None

def analyze_plant_gemini(image_pil, api_key):
    try:
        genai.configure(api_key=api_key.strip())
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        model_name = next((m for m in available_models if "flash" in m), available_models[0])
        model = genai.GenerativeModel(model_name)
        prompt = "Identify this plant and provide: [NAME], [FLOURISH], [FORBIDDEN], [MANAGE], [PRUNE_FEED], [GLORIOUS], [PRIME], and [MAP]."
        response = model.generate_content([prompt, image_pil])
        return response.text
    except Exception as e: return f"ERROR: {str(e)}"

# --- SIDEBAR ---
with st.sidebar:
    st.title("🌿 Settings")
    saved_key = st.session_state.config.get("api_key", "")
    api_key = st.text_input("Gemini API Key", value=saved_key, type="password")
    if api_key != saved_key:
        st.session_state.config["api_key"] = api_key
        save_config(st.session_state.config)
        st.rerun()

    if st.button("⬅️ BACK TO GALLERY"):
        st.session_state.view_mode = "gallery"
        st.rerun()

    st.divider()
    st.subheader("💾 Backup")
    json_data = json.dumps(st.session_state.garden)
    st.download_button("📥 SAVE BACKUP", json_data, file_name="peters_garden_backup.json")
    uploaded_backup = st.file_uploader("📤 RESTORE", type="json")
    if uploaded_backup:
        st.session_state.garden = json.load(uploaded_backup)
        save_data(st.session_state.garden)
        st.rerun()

    st.divider()
    st.header("📸 Add Plant")
    uploaded_file = st.file_uploader("Photo", type=['jpg', 'jpeg', 'png', 'HEIC', 'heic'])
    loc = st.text_input("Location")
    if st.button("IDENTIFY & SAVE"):
        if uploaded_file and api_key:
            with st.spinner("Analyzing..."):
                image = Image.open(uploaded_file).convert('RGB')
                raw_data = analyze_plant_gemini(image, api_key)
                buf = io.BytesIO()
                image.save(buf, format="JPEG")
                img_b64 = base64.b64encode(buf.getvalue()).decode('utf-8')
                new_plant = {"id": str(datetime.now().timestamp()), "name": raw_data.split("[NAME]")[1].split("[")[0].strip(), "location": loc, "image": img_b64, "data": raw_data}
                st.session_state.garden.append(new_plant)
                save_data(st.session_state.garden)
                st.rerun()

# --- MAIN DISPLAY ---
if st.session_state.view_mode == "gallery":
    # On iPhone, show a helper if sidebar is closed
    if st.sidebar.checkbox("Show Navigation Help", value=True):
        st.info("📱 iPhone Users: Tap the tiny ARROW in the top-left to open Settings/Add Plant.")
        
    st.title("My Garden")
    search = st.text_input("🔍 Search garden...")
    display_list = [p for p in st.session_state.garden if search.lower() in p.get('name','').lower() or search.lower() in p.get('location','').lower()]
    
    cols = st.columns(1 if st.sidebar.checkbox("Mobile View (1 column)", False) else 2)
    for i, plant in enumerate(reversed(display_list)):
        with cols[i % len(cols)]:
            st.markdown('<div class="gallery-card">', unsafe_allow_html=True)
            img = get_any_image(plant)
            if img: st.image(base64.b64decode(img), use_container_width=True)
            st.markdown(f"### {plant.get('name', 'Unknown')}")
            st.markdown(f"<p>📍 {plant.get('location', 'Unknown')}</p>", unsafe_allow_html=True)
            if st.button("VIEW DETAILS", key=f"v_{i}"):
                st.session_state.selected_plant = plant
                st.session_state.view_mode = "details"
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
else:
    p = st.session_state.selected_plant
    st.title(p['name'])
    st.markdown(f'<div style="background-color:#1E3A8A; padding:10px; border-radius:8px; display:inline-block;">📍 {p.get("location", "Lounge")}</div>', unsafe_allow_html=True)
    c1, c2 = st.columns([1, 1.2])
    with c1:
        img = get_any_image(p)
        if img: st.image(base64.b64decode(img), use_container_width=True)
        st.divider()
        search_url = f"https://www.google.com/search?tbm=isch&q={urllib.parse.quote(p['name'] + ' plant mature')}"
        st.link_button("🌐 VIEW PRIME PHOTOS", search_url)
    with c2:
        def gs(sec): 
            try: return p['data'].split(f"[{sec}]")[1].split("[")[0].strip()
            except: return "Pending..."
        st.markdown(f'<div class="box box-flourish"><span class="header-label">🌿 TO FLOURISH</span>{gs("FLOURISH")}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="box box-forbidden"><span class="header-label">🚫 FORBIDDEN</span>{gs("FORBIDDEN")}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="box box-prune"><span class="header-label">✂️ PRUNE & FEED</span>{gs("PRUNE_FEED")}</div>', unsafe_allow_html=True)
        with st.expander("📍 VIEW PRUNING MAP"): st.warning(gs('MAP'))
        if st.button("🗑️ DELETE PLANT"):
            st.session_state.garden = [x for x in st.session_state.garden if x['id'] != p['id']]
            save_data(st.session_state.garden)
            st.session_state.view_mode = "gallery"
            st.rerun()
