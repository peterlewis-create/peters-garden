import streamlit as st
import google.generativeai as genai
import base64
import json
from PIL import Image
import io
import urllib.parse
from supabase import create_client, Client

# 1. PAGE SETUP
st.set_page_config(page_title="Peter's Garden", layout="wide", page_icon="🌿")

# 2. PERMANENT CLOUD CONNECTION (Loads from your Vault)
try:
    URL = st.secrets["SB_URL"].strip()
    KEY = st.secrets["SB_KEY"].strip()
    G_KEY = st.secrets["GEMINI_KEY"].strip()
    supabase: Client = create_client(URL, KEY)
except Exception as e:
    st.error("Setup your Keys in Streamlit Settings > Secrets to activate Cloud Sync.")
    st.stop()

# 3. HIGH CONTRAST STYLING (The Look)
st.markdown("""
    <style>
    .stApp, [data-testid="stSidebar"] { background-color: #000000 !important; }
    p, li, h1, h2, h3, span, label, div, .stMarkdown { color: #FFFFFF !important; }
    
    /* THE BUTTON FIX: Black background, White text, White border */
    button { 
        background-color: #000000 !important; 
        color: #FFFFFF !important; 
        border: 2px solid #FFFFFF !important; 
        border-radius: 8px !important;
        padding: 10px 20px !important;
    }
    
    .gallery-card { 
        background-color: #111111; 
        padding: 15px; 
        border-radius: 15px; 
        border: 2px solid #333333; 
        text-align: center; 
        margin-bottom: 30px; 
    }
    
    .box { padding: 20px; border-radius: 12px; margin-bottom: 20px; border: 4px solid; background-color: #000000; }
    .box-flourish { border-color: #22C55E; }
    .box-forbidden { border-color: #EF4444; }
    .box-prune { border-color: #3B82F6; }
    .header-label { font-weight: 900; color: #FFFFFF !important; font-size: 1.3rem; text-transform: uppercase; }
    input { background-color: #222222 !important; color: white !important; }
    </style>
    """, unsafe_allow_html=True)

# 4. DATABASE HELPERS (The Engine)
def fetch_garden():
    try:
        res = supabase.table("garden_table").select("*").order("created_at", ascending=False).execute()
        return res.data
    except: return []

def add_to_cloud(name, loc, img, data):
    supabase.table("garden_table").insert({"name": str(name), "location": str(loc), "image": str(img), "data": str(data)}).execute()

def get_safe_image(plant):
    # This logic is what restored your 24 photos
    if plant.get('image'): return plant['image']
    if 'history' in plant and len(plant['history']) > 0: return plant['history'][-1]['image']
    return None

# 5. NAVIGATION
if "view_mode" not in st.session_state: st.session_state.view_mode = "gallery"

with st.sidebar:
    st.title("🌿 Peter's Garden")
    data = fetch_garden()
    st.metric("Plants in Cloud", len(data))
    
    if st.button("🔄 REFRESH GALLERY"): st.rerun()
    if st.button("⬅️ BACK TO GALLERY"): 
        st.session_state.view_mode = "gallery"
        st.rerun()

    st.divider()
    st.header("📸 Add New Plant")
    pic = st.file_uploader("Upload Photo", type=['jpg', 'jpeg', 'png', 'HEIC', 'heic'])
    loc_in = st.text_input("Location")
    if st.button("IDENTIFY & SAVE"):
        if pic:
            with st.spinner("AI Analysis..."):
                genai.configure(api_key=G_KEY)
                model = genai.GenerativeModel('models/gemini-1.5-flash')
                img_obj = Image.open(pic).convert('RGB')
                res = model.generate_content(["Identify this plant and give care tips using: [NAME], [FLOURISH], [FORBIDDEN], [PRUNE_FEED], [MAP].", img_obj])
                
                buf = io.BytesIO()
                img_obj.save(buf, format="JPEG", quality=30)
                img_b64 = base64.b64encode(buf.getvalue()).decode('utf-8')
                
                try: p_name = res.text.split("[NAME]")[1].split("[")[0].strip().replace("**", "")
                except: p_name = "New Plant"
                
                add_to_cloud(p_name, loc_in, img_b64, res.text)
                st.rerun()

# 6. DISPLAY
if st.session_state.view_mode == "gallery":
    st.title("My Garden")
    search = st.text_input("🔍 Search garden...")
    display_list = [p for p in data if search.lower() in p['name'].lower()]
    
    cols = st.columns(2)
    for i, plant in enumerate(display_list):
        with cols[i % 2]:
            st.markdown('<div class="gallery-card">', unsafe_allow_html=True)
            img = get_safe_image(plant)
            if img: st.image(base64.b64decode(img), use_container_width=True)
            st.subheader(plant['name'])
            st.write(f"📍 {plant['location']}")
            if st.button("DETAILS", key=f"v_{plant['id']}"):
                st.session_state.selected_plant = plant
                st.session_state.view_mode = "details"
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
else:
    # DETAIL VIEW
    p = st.session_state.selected_plant
    st.title(p['name'])
    st.markdown(f'<div style="background-color:#1E3A8A; padding:10px; border-radius:8px; display:inline-block;">📍 {p["location"]}</div>', unsafe_allow_html=True)
    c1, c2 = st.columns([1, 1.2])
    with c1:
        img = get_safe_image(p)
        if img: st.image(base64.b64decode(img), use_container_width=True)
        search_url = f"https://www.google.com/search?tbm=isch&q={urllib.parse.quote(p['name'] + ' plant mature')}"
        st.link_button("🌐 VIEW PRIME PHOTOS", search_url)
        if st.button("🗑️ DELETE"):
            supabase.table("garden_table").delete().eq("id", p['id']).execute()
            st.session_state.view_mode = "gallery"
            st.rerun()
    with c2:
        def gs(sec): 
            try: return p['data'].split(f"[{sec}]")[1].split("[")[0].strip().replace("**", "")
            except: return None
        
        flourish = gs("FLOURISH")
        if flourish:
            st.markdown(f'<div class="box box-flourish"><span class="header-label">🌿 TO FLOURISH</span><br>{flourish}</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="box box-forbidden"><span class="header-label">🚫 FORBIDDEN</span><br>{gs("FORBIDDEN")}</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="box box-prune"><span class="header-label">✂️ PRUNE & FEED</span><br>{gs("PRUNE_FEED")}</div>', unsafe_allow_html=True)
            with st.expander("📍 VIEW PRUNING MAP"): st.warning(gs('MAP'))
        else:
            st.info("Plant Details")
            st.write(p['data'])
