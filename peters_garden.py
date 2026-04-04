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

# 2. LOAD SECRETS
try:
    SB_URL = st.secrets["SB_URL"].strip()
    SB_KEY = st.secrets["SB_KEY"].strip()
    GEMINI_KEY = st.secrets["GEMINI_KEY"].strip()
    supabase: Client = create_client(SB_URL, SB_KEY)
except Exception as e:
    st.error(f"Credentials Error: {e}")
    st.stop()

# 3. HIGH CONTRAST STYLING
st.markdown("""
    <style>
    .stApp, [data-testid="stSidebar"], .stMarkdown { background-color: #000000 !important; }
    p, li, h1, h2, h3, span, label, div, .stMarkdown { color: #FFFFFF !important; }
    button { background-color: #111111 !important; color: #FFFFFF !important; border: 1px solid #FFFFFF !important; border-radius: 8px !important; }
    .gallery-card { background-color: #111111; padding: 15px; border-radius: 15px; border: 2px solid #333333; text-align: center; margin-bottom: 30px; }
    .box { padding: 20px; border-radius: 12px; margin-bottom: 20px; border: 4px solid; background-color: #000000; }
    .box-flourish { border-color: #22C55E; }
    .box-forbidden { border-color: #EF4444; }
    .box-prune { border-color: #3B82F6; }
    .header-label { font-weight: 900; color: #FFFFFF !important; font-size: 1.3rem; text-transform: uppercase; margin-bottom: 10px; display: block; }
    input { background-color: #222222 !important; color: white !important; }
    </style>
    """, unsafe_allow_html=True)

# 4. DATABASE & AI
def fetch_garden():
    try:
        res = supabase.table("garden_table").select("*").order("created_at", ascending=False).execute()
        return res.data
    except: return []

def add_to_cloud(name, loc, img, data):
    supabase.table("garden_table").insert({"name": str(name), "location": str(loc), "image": str(img), "data": str(data)}).execute()

def analyze_plant_gemini(image_pil, api_key):
    try:
        genai.configure(api_key=api_key)
        # Try multiple model addresses to find the working one
        for model_name in ['models/gemini-1.5-flash', 'gemini-1.5-flash']:
            try:
                model = genai.GenerativeModel(model_name)
                response = model.generate_content(["Identify this plant and provide care tips using these tags: [NAME], [FLOURISH], [FORBIDDEN], [PRUNE_FEED], [MAP].", image_pil])
                return response.text
            except: continue
        return "ERROR: AI Brain not responding."
    except Exception as e: return f"ERROR: {str(e)}"

def get_sec(text, sec):
    try:
        if f"[{sec}]" in text:
            return text.split(f"[{sec}]")[1].split("[")[0].strip().replace("**", "")
        return None
    except: return None

# 5. NAVIGATION
if "view_mode" not in st.session_state: st.session_state.view_mode = "gallery"

# --- SIDEBAR ---
with st.sidebar:
    st.title("🌿 Peter's Garden")
    
    # Connection Meter
    garden_data = fetch_garden()
    st.metric("Total Plants in Cloud", len(garden_data))
    
    if st.button("🔄 REFRESH GALLERY"): st.rerun()
    if st.button("⬅️ BACK TO GALLERY"): 
        st.session_state.view_mode = "gallery"
        st.rerun()

    st.divider()
    st.subheader("🚀 Migration Tool")
    uploaded_json = st.file_uploader("Upload Desktop JSON", type="json")
    if uploaded_json and st.button("Start Moving Plants"):
        data_list = json.load(uploaded_json)
        prog = st.progress(0)
        for i, p in enumerate(data_list):
            p_name = p.get('name', 'Plant').replace("**", "")
            img = p.get('image') or (p['history'][-1].get('image') if 'history' in p else "")
            # Shrink images for Cloud
            if img:
                try:
                    decoded = base64.b64decode(img)
                    temp_img = Image.open(io.BytesIO(decoded))
                    buf = io.BytesIO()
                    temp_img.save(buf, format="JPEG", quality=20)
                    img = base64.b64encode(buf.getvalue()).decode('utf-8')
                except: pass
            add_to_cloud(p_name, p.get('location', 'Lounge'), img, p.get('data', ''))
            prog.progress((i + 1) / len(data_list))
        st.rerun()

    st.divider()
    st.header("📸 Add Plant")
    uploaded_file = st.file_uploader("Take Photo", type=['jpg', 'jpeg', 'png', 'HEIC', 'heic'])
    loc_input = st.text_input("Location")
    if st.button("IDENTIFY & SAVE"):
        if uploaded_file:
            with st.spinner("Analyzing..."):
                image = Image.open(uploaded_file).convert('RGB')
                raw_ai = analyze_plant_gemini(image, GEMINI_KEY)
                buf = io.BytesIO()
                image.save(buf, format="JPEG", quality=30)
                img_b64 = base64.b64encode(buf.getvalue()).decode('utf-8')
                p_name = get_sec(raw_ai, "NAME") or "New Plant"
                add_to_cloud(p_name, loc_input, img_b64, raw_ai)
                st.rerun()

# 6. DISPLAY
if st.session_state.view_mode == "gallery":
    st.title("My Garden")
    search = st.text_input("🔍 Search garden...")
    display_list = [p for p in garden_data if search.lower() in p.get('name','').lower()]
    
    if not display_list: st.info("The gallery is empty. Check sidebar count.")
    
    cols = st.columns(2)
    for i, plant in enumerate(display_list):
        with cols[i % 2]:
            st.markdown('<div class="gallery-card">', unsafe_allow_html=True)
            if plant.get('image'): st.image(base64.b64decode(plant['image']), use_container_width=True)
            st.subheader(plant.get('name', 'Plant'))
            st.markdown(f"📍 {plant.get('location', 'Lounge')}")
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
        if p.get('image'): st.image(base64.b64decode(p['image']), use_container_width=True)
        search_url = f"https://www.google.com/search?tbm=isch&q={urllib.parse.quote(str(p['name']) + ' plant mature')}"
        st.link_button("🌐 VIEW PRIME PHOTOS", search_url)
        if st.button("🗑️ DELETE"):
            supabase.table("garden_table").delete().eq("id", p['id']).execute()
            st.session_state.view_mode = "gallery"
            st.rerun()
    with c2:
        d = p.get('data', '')
        flourish = get_sec(d, "FLOURISH")
        if flourish:
            st.markdown(f'<div class="box box-flourish"><span class="header-label">🌿 TO FLOURISH</span>{flourish}</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="box box-forbidden"><span class="header-label">🚫 FORBIDDEN</span>{get_sec(d, "FORBIDDEN") or "None"}</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="box box-prune"><span class="header-label">✂️ PRUNE & FEED</span>{get_sec(d, "PRUNE_FEED") or "None"}</div>', unsafe_allow_html=True)
            with st.expander("📍 VIEW PRUNING MAP"): st.warning(get_sec(d, 'MAP') or "No specific map available.")
        else:
            st.info("Plant Details")
            st.write(d)
