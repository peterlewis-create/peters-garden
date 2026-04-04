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

# 3. ADVANCED MOBILE VISIBILITY STYLING
st.markdown("""
    <style>
    /* 1. Global Backgrounds */
    .stApp { background-color: #000000 !important; }
    
    /* 2. Sidebar Visibility (iPad/iPhone Fix) */
    [data-testid="stSidebar"] {
        background-color: #111111 !important;
        border-right: 1px solid #333333;
    }
    
    /* 3. Force Sidebar Text to be Pure White */
    [data-testid="stSidebar"] p, 
    [data-testid="stSidebar"] span, 
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2 {
        color: #FFFFFF !important;
    }

    /* 4. iPhone Sidebar Toggle Button (The 'Open' Arrow) */
    /* We make this Neon Green so you can see it on your iPhone */
    button[kind="headerNoContext"] {
        background-color: #22C55E !important;
        color: #000000 !important;
        border-radius: 50% !important;
        border: 2px solid white !important;
    }

    /* 5. Main Screen Text Visibility */
    p, li, h1, h2, h3, span, label, div, .stMarkdown { color: #FFFFFF !important; }
    
    /* 6. Plant Card Styling */
    .gallery-card {
        background-color: #111111;
        padding: 15px;
        border-radius: 15px;
        border: 2px solid #444444;
        text-align: center;
        margin-bottom: 25px;
    }

    /* 7. Dashboard Boxes */
    .box { padding: 20px; border-radius: 12px; margin-bottom: 20px; border: 4px solid; background-color: #000000; }
    .box-flourish { border-color: #22C55E; }
    .box-forbidden { border-color: #EF4444; }
    .box-prune { border-color: #3B82F6; }
    .header-label { font-weight: 900; color: #FFFFFF !important; font-size: 1.4rem; text-transform: uppercase; margin-bottom: 10px; display: block; }
    
    /* 8. Input Visibility */
    input, textarea { 
        background-color: #222222 !important; 
        color: #FFFFFF !important; 
        border: 1px solid #007AFF !important; 
    }
    
    /* 9. Success/Error text contrast */
    .stAlert p { color: #000000 !important; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# Helper for compatibility
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

    if st.button("⬅️ Back to Gallery"):
        st.session_state.view_mode = "gallery"
        st.rerun()

    st.divider()
    st.subheader("💾 Sync & Backup")
    json_data = json.dumps(st.session_state.garden)
    st.download_button("📥 Save Backup", json_data, file_name="peters_garden_backup.json")
    uploaded_backup = st.file_uploader("📤 Restore from Backup", type="json")
    if uploaded_backup:
        st.session_state.garden = json.load(uploaded_backup)
        save_data(st.session_state.garden)
        st.success("Success!")

    st.divider()
    st.header("📸 Add Plant")
    uploaded_file = st.file_uploader("Take Photo", type=['jpg', 'jpeg', 'png', 'HEIC', 'heic'])
    loc = st.text_input("Location")
    if st.button("Identify & Save"):
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
    st.title("My Garden")
    search = st.text_input("🔍 Search garden...")
    display_list = [p for p in st.session_state.garden if search.lower() in p.get('name','').lower() or search.lower() in p.get('location','').lower()]
    cols = st.columns(2 if st.sidebar.checkbox("Large View", False) else 3)
    for i, plant in enumerate(reversed(display_list)):
        with cols[i % len(cols)]:
            st.markdown('<div class="gallery-card">', unsafe_allow_html=True)
            img = get_any_image(plant)
            if img: st.image(base64.b64decode(img), use_container_width=True)
            st.subheader(plant.get('name', 'Unknown'))
            st.caption(f"📍 {plant.get('location', 'Unknown')}")
            if st.button("View Details", key=f"v_{i}"):
                st.session_state.selected_plant = plant
                st.session_state.view_mode = "details"
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
else:
    p = st.session_state.selected_plant
    st.title(p['name'])
    st.markdown(f'<div class="loc-badge">📍 {p.get("location", "Lounge Area")}</div>', unsafe_allow_html=True)
    c1, c2 = st.columns([1, 1.5])
    with c1:
        img = get_any_image(p)
        if img: st.image(base64.b64decode(img), use_container_width=True)
        st.divider()
        st.subheader("🌟 IN ITS PRIME")
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
        if st.button("🗑️ Delete Plant"):
            st.session_state.garden = [x for x in st.session_state.garden if x['id'] != p['id']]
            save_data(st.session_state.garden)
            st.session_state.view_mode = "gallery"
            st.rerun()
