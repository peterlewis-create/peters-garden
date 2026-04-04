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

# 2. LOAD MASTER KEYS FROM VAULT
try:
    SB_URL = st.secrets["SB_URL"].strip()
    SB_KEY = st.secrets["SB_KEY"].strip()
    GEMINI_KEY = st.secrets["GEMINI_KEY"].strip()
    # Create the Cloud Client
    supabase: Client = create_client(SB_URL, SB_KEY)
except Exception as e:
    st.error("🔌 Sync Error: Keys are missing in the Streamlit Vault.")
    st.stop()

# 3. HIGH CONTRAST STYLING
st.markdown("""
    <style>
    .stApp, [data-testid="stSidebar"], .stMarkdown { background-color: #000000 !important; }
    p, li, h1, h2, h3, span, label, div, .stMarkdown { color: #FFFFFF !important; }
    button { background-color: #111111 !important; color: #FFFFFF !important; border: 1px solid #FFFFFF !important; border-radius: 8px !important; }
    .gallery-card { background-color: #111111; padding: 15px; border-radius: 15px; border: 2px solid #333333; text-align: center; margin-bottom: 30px; min-height: 400px;}
    .box { padding: 20px; border-radius: 12px; margin-bottom: 20px; border: 4px solid; background-color: #000000; }
    .box-flourish { border-color: #22C55E; }
    .box-forbidden { border-color: #EF4444; }
    .box-prune { border-color: #3B82F6; }
    .header-label { font-weight: 900; color: #FFFFFF !important; font-size: 1.3rem; text-transform: uppercase; margin-bottom: 10px; display: block; }
    </style>
    """, unsafe_allow_html=True)

# 4. DATABASE HELPERS
def fetch_garden():
    try:
        # Fetching directly from cloud table
        res = supabase.table("garden_table").select("*").order("created_at", ascending=False).execute()
        return res.data
    except: return []

def add_to_cloud(name, loc, img_b64, data):
    try:
        supabase.table("garden_table").insert({
            "name": str(name), "location": str(loc), "image": str(img_b64), "data": str(data)
        }).execute()
        return True
    except: return False

def get_safe_image(plant):
    # This recovers photos from all previous versions of the app
    if plant.get('image'): return plant['image']
    if 'history' in plant and len(plant['history']) > 0: return plant['history'][-1]['image']
    return None

# 5. AI BRAIN
def analyze_plant_gemini(image_pil, api_key):
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('models/gemini-1.5-flash')
        prompt = "Identify this plant and provide care tips using these tags: [NAME], [FLOURISH], [FORBIDDEN], [PRUNE_FEED], [MAP]."
        response = model.generate_content([prompt, image_pil])
        return response.text
    except: return "ERROR: AI brain not responding."

def get_sec(text, sec):
    try:
        if f"[{sec}]" in text:
            return text.split(f"[{sec}]")[1].split("[")[0].strip().replace("**", "")
        return None
    except: return None

# 6. APP LOGIC
if "view_mode" not in st.session_state: st.session_state.view_mode = "gallery"

with st.sidebar:
    st.title("🌿 Peter's Garden")
    
    # Show Cloud Count
    current_data = fetch_garden()
    st.metric("Total Plants in Cloud", len(current_data))
    
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
            img = get_safe_image(p)
            if img: # Shrink for Cloud
                try:
                    decoded = base64.b64decode(img)
                    temp_img = Image.open(io.BytesIO(decoded))
                    buf = io.BytesIO()
                    temp_img.save(buf, format="JPEG", quality=20)
                    img = base64.b64encode(buf.getvalue()).decode('utf-8')
                except: pass
            add_to_cloud(p_name, p.get('location', 'Lounge'), img, p.get('data', ''))
            prog.progress((i + 1) / len(data_list))
        st.success("Migration complete! Click Refresh.")
        st.rerun()

    st.divider()
    st.header("📸 Add Plant")
    pic = st.file_uploader("Take Photo", type=['jpg', 'jpeg', 'png', 'HEIC', 'heic'])
    loc_in = st.text_input("Location")
    if st.button("IDENTIFY & SAVE"):
        if pic:
            with st.spinner("Analyzing..."):
                img_obj = Image.open(pic).convert('RGB')
                raw_ai = analyze_plant_gemini(img_obj, GEMINI_KEY)
                buf = io.BytesIO()
                img_obj.save(buf, format="JPEG", quality=30)
                img_b64 = base64.b64encode(buf.getvalue()).decode('utf-8')
                p_name = get_sec(raw_ai, "NAME") or "New Plant"
                add_to_cloud(p_name, loc_in, img_b64, raw_ai)
                st.rerun()

# 7. MAIN DISPLAY
if st.session_state.view_mode == "gallery":
    st.title("My Garden")
    search = st.text_input("🔍 Search garden...")
    display_list = [p for p in current_data if search.lower() in p['name'].lower()]
    
    if not display_list:
        st.info("The Cloud gallery is empty. Use the sidebar to upload your JSON file.")
    
    cols = st.columns(2)
    for i, plant in enumerate(display_list):
        with cols[i % 2]:
            st.markdown('<div class="gallery-card">', unsafe_allow_html=True)
            img = get_safe_image(plant)
            if img: st.image(base64.b64decode(img), use_container_width=True)
            st.subheader(plant['name'])
            st.caption(f"📍 {plant['location']}")
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
        img = get_safe_image(p)
        if img: st.image(base64.b64decode(img), use_container_width=True)
        search_url = f"https://www.google.com/search?tbm=isch&q={urllib.parse.quote(p['name'] + ' plant mature')}"
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
            st.markdown(f'<div class="box box-forbidden"><span class="header-label">🚫 FORBIDDEN</span>{get_sec(d, "FORBIDDEN")}</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="box box-prune"><span class="header-label">✂️ PRUNE & FEED</span>{get_sec(d, "PRUNE_FEED")}</div>', unsafe_allow_html=True)
            with st.expander("📍 VIEW PRUNING MAP"): st.warning(get_sec(d, 'MAP'))
        else:
            st.info("Migrated Information")
            st.write(d)
