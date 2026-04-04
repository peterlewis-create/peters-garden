import streamlit as st
import google.generativeai as genai
import base64
import json
import os
from datetime import datetime
from PIL import Image
import io
import urllib.parse

# 1. HEIC support for Mac/iPhone
try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
except: pass

# 2. Database & Config Files
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

# Initialize Session States
if "garden" not in st.session_state: st.session_state.garden = load_data()
if "config" not in st.session_state: st.session_state.config = load_config()
if "view_mode" not in st.session_state: st.session_state.view_mode = "gallery"
if "selected_plant" not in st.session_state: st.session_state.selected_plant = None

st.set_page_config(page_title="Peter's Garden", layout="wide", page_icon="🌿")

# 3. HIGH CONTRAST STYLING (Pure White on Pure Black)
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
    button { color: #000000 !important; font-weight: bold !important; }
    </style>
    """, unsafe_allow_html=True)

# 4. HELPERS
def get_any_image(plant):
    if plant.get('image'): return plant['image']
    if 'history' in plant and len(plant['history']) > 0: return plant['history'][-1]['image']
    return None

def get_sec(text, sec):
    try: return text.split(f"[{sec}]")[1].split("[")[0].strip()
    except: return "Information coming soon..."

# 5. AI ENGINE
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

# 6. SIDEBAR
with st.sidebar:
    st.header("🌿 Peter's Garden")
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
    st.header("📸 Add a Plant")
    uploaded_file = st.file_uploader("Upload photo", type=['jpg', 'jpeg', 'png', 'HEIC', 'heic'])
    loc = st.text_input("Location (e.g. Lounge Area)")
    if st.button("Identify & Add to Database"):
        if uploaded_file and api_key:
            with st.spinner("AI analyzing..."):
                image = Image.open(uploaded_file).convert('RGB')
                raw_data = analyze_plant_gemini(image, api_key)
                if "ERROR" in raw_data: st.error(raw_data)
                else:
                    buf = io.BytesIO()
                    image.save(buf, format="JPEG")
                    img_b64 = base64.b64encode(buf.getvalue()).decode('utf-8')
                    new_plant = {"id": str(datetime.now().timestamp()), "name": get_sec(raw_data, "NAME"), "location": loc, "image": img_b64, "data": raw_data}
                    st.session_state.garden.append(new_plant)
                    save_data(st.session_state.garden)
                    st.success("Added!")
                    st.rerun()

# 7. MAIN LOGIC
if st.session_state.view_mode == "gallery":
    st.title("My Garden")
    search = st.text_input("🔍 Search garden (Type name or room)...")
    
    # Filter list
    display_list = [p for p in st.session_state.garden if p.get('name') and (search.lower() in p['name'].lower() or search.lower() in p.get('location', '').lower())]
    
    if not display_list:
        st.write("Your garden is empty. Add a plant using the sidebar!")
    else:
        cols = st.columns(3)
        for i, plant in enumerate(reversed(display_list)):
            with cols[i % 3]:
                st.markdown('<div class="gallery-card">', unsafe_allow_html=True)
                img_data = get_any_image(plant)
                if img_data:
                    st.image(base64.b64decode(img_data), use_container_width=True)
                st.subheader(plant.get('name', 'Unknown'))
                st.caption(f"📍 {plant.get('location', 'Unknown')}")
                if st.button(f"View Details", key=f"view_{plant.get('id', i)}"):
                    st.session_state.selected_plant = plant
                    st.session_state.view_mode = "details"
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)
else:
    # 8. DETAIL VIEW
    plant = st.session_state.selected_plant
    st.title(plant.get('name', 'Unknown'))
    st.markdown(f'<div class="loc-badge">📍 {plant.get("location", "Unknown")}</div>', unsafe_allow_html=True)
    
    col_left, col_right = st.columns([1, 1.5])
    with col_left:
        img_data = get_any_image(plant)
        if img_data:
            st.image(base64.b64decode(img_data), use_container_width=True, caption="YOUR PLANT")
        
        st.divider()
        st.header("🌟 IN ITS PRIME")
        st.write(get_sec(plant.get('data', ''), 'PRIME'))
        
        # STABLE PRIME PHOTO BUTTON
        search_url = f"https://www.google.com/search?tbm=isch&q={urllib.parse.quote(plant.get('name', '') + ' plant mature prime')}"
        st.link_button("🌐 VIEW PRIME PHOTOS ON WEB", search_url)
        
        st.divider()
        if st.button("🗑️ Delete Plant"):
            st.session_state.garden = [p for p in st.session_state.garden if p.get('id') != plant.get('id')]
            save_data(st.session_state.garden)
            st.session_state.view_mode = "gallery"
            st.rerun()
            
    with col_right:
        st.markdown(f'<div class="box box-flourish"><span class="header-label">🌿 TO FLOURISH</span>{get_sec(plant.get("data", ""), "FLOURISH")}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="box box-forbidden"><span class="header-label">🚫 FORBIDDEN</span>{get_sec(plant.get("data", ""), "FORBIDDEN")}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="box box-prune"><span class="header-label">✂️ PRUNE & FEED</span>{get_sec(plant.get("data", ""), "PRUNE_FEED")}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="box box-glorious"><span class="header-label">✨ GLORIOUS TIPS</span>{get_sec(plant.get("data", ""), "GLORIOUS")}</div>', unsafe_allow_html=True)
        
        with st.expander("📍 VIEW PRUNING MAP"):
            st.warning(get_sec(plant.get('data', ''), 'MAP'))