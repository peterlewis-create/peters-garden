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

if "garden" not in st.session_state: st.session_state.garden = load_data()
if "view_mode" not in st.session_state: st.session_state.view_mode = "gallery"
if "selected_plant" not in st.session_state: st.session_state.selected_plant = None

st.set_page_config(page_title="Peter's Garden", layout="wide", page_icon="🌿")

# 3. STYLING
st.markdown("""
    <style>
    .stApp { background-color: #000000 !important; }
    p, li, h1, h2, h3, span, label, div, .stMarkdown { color: #FFFFFF !important; font-family: 'Helvetica Neue', Arial; }
    .gallery-card { background-color: #111111; padding: 15px; border-radius: 15px; border: 2px solid #444444; text-align: center; margin-bottom: 25px; }
    .box { padding: 20px; border-radius: 12px; margin-bottom: 20px; border: 4px solid; background-color: #000000; }
    .box-flourish { border-color: #22C55E; }
    .box-forbidden { border-color: #EF4444; }
    .box-prune { border-color: #3B82F6; }
    .box-glorious { border-color: #FACC15; }
    .header-label { font-weight: 900; color: #FFFFFF !important; font-size: 1.4rem; text-transform: uppercase; margin-bottom: 10px; display: block; }
    .loc-badge { font-size: 1.5rem !important; font-weight: bold; background-color: #1E3A8A; padding: 10px 20px; border-radius: 10px; border: 1px solid #3B82F6; display: inline-block; margin-bottom: 25px; }
    input { background-color: #222222 !important; color: white !important; }
    </style>
    """, unsafe_allow_html=True)

# 4. HELPERS
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

# 5. SIDEBAR (With Data Sync)
with st.sidebar:
    st.header("🌿 Peter's Garden")
    api_key = st.text_input("Gemini API Key", type="password")
    
    if st.button("⬅️ Back to Gallery"):
        st.session_state.view_mode = "gallery"
        st.rerun()
    
    st.divider()
    st.subheader("💾 Sync & Backup")
    # EXPORT: Download data to laptop/phone
    json_data = json.dumps(st.session_state.garden)
    st.download_button("📥 Save Backup to Device", json_data, file_name="peters_garden_backup.json")
    
    # IMPORT: Move data from laptop to phone
    uploaded_backup = st.file_uploader("📤 Restore from Backup", type="json")
    if uploaded_backup:
        st.session_state.garden = json.load(uploaded_backup)
        save_data(st.session_state.garden)
        st.success("Garden Restored!")

    st.divider()
    st.header("📸 Add a Plant")
    uploaded_file = st.file_uploader("Take Photo", type=['jpg', 'jpeg', 'png', 'HEIC', 'heic'])
    loc = st.text_input("Location")
    if st.button("Identify & Save"):
        if uploaded_file and api_key:
            with st.spinner("AI analyzing..."):
                image = Image.open(uploaded_file).convert('RGB')
                raw_data = analyze_plant_gemini(image, api_key)
                buf = io.BytesIO()
                image.save(buf, format="JPEG")
                img_b64 = base64.b64encode(buf.getvalue()).decode('utf-8')
                new_plant = {"id": str(datetime.now().timestamp()), "name": raw_data.split("[NAME]")[1].split("[")[0].strip(), "location": loc, "image": img_b64, "data": raw_data}
                st.session_state.garden.append(new_plant)
                save_data(st.session_state.garden)
                st.rerun()

# 6. GALLERY & DETAILS
if st.session_state.view_mode == "gallery":
    st.title("My Garden")
    search = st.text_input("🔍 Search garden...")
    display_list = [p for p in st.session_state.garden if search.lower() in p.get('name','').lower()]
    cols = st.columns(2 if st.sidebar.checkbox("Large View", False) else 3)
    for i, plant in enumerate(reversed(display_list)):
        with cols[i % len(cols)]:
            st.markdown('<div class="gallery-card">', unsafe_allow_html=True)
            img = get_any_image(plant)
            if img: st.image(base64.b64decode(img), use_container_width=True)
            st.subheader(plant.get('name', 'Unknown'))
            if st.button("View Details", key=f"v_{i}"):
                st.session_state.selected_plant = plant
                st.session_state.view_mode = "details"
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
else:
    p = st.session_state.selected_plant
    st.title(p['name'])
    st.markdown(f'<div class="loc-badge">📍 {p.get("location", "Lounge")}</div>', unsafe_allow_html=True)
    c1, c2 = st.columns([1, 1.5])
    with c1:
        img = get_any_image(p)
        if img: st.image(base64.b64decode(img), use_container_width=True)
        search_url = f"https://www.google.com/search?tbm=isch&q={urllib.parse.quote(p['name'] + ' plant mature')}"
        st.link_button("🌐 VIEW PRIME PHOTOS", search_url)
    with c2:
        def gs(sec): return p['data'].split(f"[{sec}]")[1].split("[")[0].strip()
        st.markdown(f'<div class="box box-flourish"><span class="header-label">🌿 TO FLOURISH</span>{gs("FLOURISH")}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="box box-forbidden"><span class="header-label">🚫 FORBIDDEN</span>{gs("FORBIDDEN")}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="box box-prune"><span class="header-label">✂️ PRUNE & FEED</span>{gs("PRUNE_FEED")}</div>', unsafe_allow_html=True)
        with st.expander("📍 VIEW PRUNING MAP"): st.warning(gs('MAP'))
