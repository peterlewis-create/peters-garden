import streamlit as st
import google.generativeai as genai
import base64
import json
from datetime import datetime
from PIL import Image
import io
import urllib.parse
from supabase import create_client, Client

# --- PETER'S PERMANENT DATABASE DETAILS ---
SB_URL = "https://fgonjbqlwcbmamtpfykn.supabase.co"
SB_KEY = "sb_publishable_uk0-o2scZSQNdTm_lgIrgw_xtg4uM6_Y9oY64"

# 1. PAGE SETUP
st.set_page_config(page_title="Peter's Garden", layout="wide", page_icon="🌿")
supabase: Client = create_client(SB_URL, SB_KEY)

# 2. HIGH CONTRAST STYLING
st.markdown("""
    <style>
    .stApp, [data-testid="stSidebar"], .stMarkdown { background-color: #000000 !important; }
    p, li, h1, h2, h3, span, label, div, .stMarkdown { color: #FFFFFF !important; }
    button { background-color: #111111 !important; color: #FFFFFF !important; border: 1px solid #FFFFFF !important; border-radius: 8px !important; }
    .gallery-card { background-color: #000000; padding: 15px; border-radius: 15px; border: 2px solid #333333; text-align: center; margin-bottom: 30px; }
    .box { padding: 20px; border-radius: 12px; margin-bottom: 20px; border: 4px solid; background-color: #000000; }
    .box-flourish { border-color: #22C55E; }
    .box-forbidden { border-color: #EF4444; }
    .box-prune { border-color: #3B82F6; }
    .header-label { font-weight: 900; color: #FFFFFF !important; font-size: 1.3rem; text-transform: uppercase; margin-bottom: 10px; display: block; }
    [data-testid="stSidebarCollapsedControl"] { background-color: #22C55E !important; }
    input { background-color: #222222 !important; color: white !important; }
    </style>
    """, unsafe_allow_html=True)

# 3. DATABASE FUNCTIONS
def fetch_garden():
    try:
        res = supabase.table("garden_table").select("*").order("created_at", ascending=False).execute()
        return res.data
    except: return []

def add_to_cloud(name, loc, img, data):
    try:
        supabase.table("garden_table").insert({
            "name": name, "location": loc, "image": img, "data": data
        }).execute()
    except Exception as e:
        st.error(f"Sync Error: {e}")

# 4. AI ENGINE
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

# 5. SIDEBAR
if "view_mode" not in st.session_state: st.session_state.view_mode = "gallery"

with st.sidebar:
    st.title("🌿 Settings")
    gemini_key = st.text_input("Paste Gemini API Key", type="password")
    
    if st.button("⬅️ BACK TO GALLERY"):
        st.session_state.view_mode = "gallery"
        st.rerun()

    st.divider()
    st.subheader("💾 Cloud Sync & Tools")
    
    uploaded_old_data = st.file_uploader("📤 Upload Desktop JSON", type="json")
    if uploaded_old_data:
        old_plants = json.load(uploaded_old_data)
        count = 0
        with st.spinner("Moving plants to Cloud..."):
            for p in old_plants:
                if p.get('name'):
                    img = p.get('image') or (p['history'][-1]['image'] if 'history' in p else None)
                    add_to_cloud(p['name'], p.get('location', 'Garden'), img, p.get('data', ''))
                    count += 1
            st.success(f"Restored {count} plants to the Cloud!")
            st.rerun()

    st.divider()
    st.header("📸 Add Plant")
    uploaded_file = st.file_uploader("Take Photo", type=['jpg', 'jpeg', 'png', 'HEIC', 'heic'])
    loc_input = st.text_input("Location")
    
    if st.button("IDENTIFY & SAVE"):
        if uploaded_file and gemini_key:
            with st.spinner("Identifying..."):
                image = Image.open(uploaded_file).convert('RGB')
                raw_data = analyze_plant_gemini(image, gemini_key)
                buf = io.BytesIO()
                image.save(buf, format="JPEG", quality=40) # Compress for cloud speed
                img_b64 = base64.b64encode(buf.getvalue()).decode('utf-8')
                try: name = raw_data.split("[NAME]")[1].split("[")[0].strip()
                except: name = "Unknown Plant"
                add_to_cloud(name, loc_input, img_b64, raw_data)
                st.rerun()

# 6. MAIN DISPLAY
garden_data = fetch_garden()

if st.session_state.view_mode == "gallery":
    st.title("My Garden")
    search = st.text_input("🔍 Search garden...")
    display_list = [p for p in garden_data if search.lower() in p['name'].lower()]
    
    if not display_list:
        st.info("Gallery is empty. Use the sidebar to upload your JSON file or add a new plant.")
    
    cols = st.columns(2)
    for i, plant in enumerate(display_list):
        with cols[i % 2]:
            st.markdown('<div class="gallery-card">', unsafe_allow_html=True)
            if plant['image']: st.image(base64.b64decode(plant['image']), use_container_width=True)
            st.markdown(f"### {plant['name']}")
            st.markdown(f"📍 {plant['location']}")
            if st.button("VIEW DETAILS", key=f"v_{plant['id']}"):
                st.session_state.selected_plant = plant
                st.session_state.view_mode = "details"
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
else:
    # DETAILS VIEW
    p = st.session_state.selected_plant
    st.title(p['name'])
    st.markdown(f'<div style="background-color:#1E3A8A; padding:10px; border-radius:8px; display:inline-block;">📍 {p["location"]}</div>', unsafe_allow_html=True)
    c1, c2 = st.columns([1, 1.2])
    with c1:
        st.image(base64.b64decode(p['image']), use_container_width=True)
        search_url = f"https://www.google.com/search?tbm=isch&q={urllib.parse.quote(p['name'] + ' plant mature')}"
        st.link_button("🌐 VIEW PRIME PHOTOS", search_url)
        if st.button("🗑️ DELETE"):
            supabase.table("garden_table").delete().eq("id", p['id']).execute()
            st.session_state.view_mode = "gallery"
            st.rerun()
    with c2:
        def gs(sec): 
            try: return p['data'].split(f"[{sec}]")[1].split("[")[0].strip()
            except: return "Data missing."
        st.markdown(f'<div class="box box-flourish"><span class="header-label">🌿 TO FLOURISH</span>{gs("FLOURISH")}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="box box-forbidden"><span class="header-label">🚫 FORBIDDEN</span>{gs("FORBIDDEN")}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="box box-prune"><span class="header-label">✂️ PRUNE & FEED</span>{gs("PRUNE_FEED")}</div>', unsafe_allow_html=True)
        with st.expander("📍 VIEW PRUNING MAP"): st.warning(gs('MAP'))
