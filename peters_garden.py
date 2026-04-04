import streamlit as st
import google.generativeai as genai
import base64
import json
from PIL import Image
import io
from supabase import create_client, Client

# 1. PAGE SETUP
st.set_page_config(page_title="Peter's Garden", layout="wide")

# 2. DIRECT CONNECTION LOGIC
try:
    # Force fresh read of secrets
    URL = st.secrets["SB_URL"].strip()
    KEY = st.secrets["SB_KEY"].strip()
    G_KEY = st.secrets["GEMINI_KEY"].strip()
    supabase: Client = create_client(URL, KEY)
except Exception as e:
    st.error(f"Credentials missing in Secrets vault: {e}")
    st.stop()

# 3. HIGH CONTRAST STYLING
st.markdown("<style>.stApp { background-color: #000000 !important; } p, li, h1, h2, h3, span, label, div { color: #FFFFFF !important; } button { background-color: #111111 !important; color: #FFFFFF !important; border: 1px solid #FFFFFF !important; } .gallery-card { background-color: #111111; padding: 15px; border-radius: 15px; border: 1px solid #444; text-align: center; margin-bottom: 30px; }</style>", unsafe_allow_html=True)

# 4. DATABASE HELPERS
def get_data():
    # Force a fresh fetch by bypassing any cache
    res = supabase.table("garden_table").select("*").execute()
    return res.data

def save_to_cloud(name, loc, img, info):
    try:
        supabase.table("garden_table").insert({
            "name": str(name), "location": str(loc), "image": str(img), "data": str(info)
        }).execute()
        return True
    except Exception as e:
        st.sidebar.error(f"Database rejected data: {e}")
        return False

# 5. SIDEBAR TOOLS
with st.sidebar:
    st.title("🌿 Peter's Garden")
    
    # THE PING TEST (Proves the connection works)
    if st.button("🧪 TEST CLOUD PING"):
        if save_to_cloud("Connection Test", "Cloud", "", "Testing connection..."):
            st.success("✅ PING SUCCESSFUL! Cloud is receiving data.")
        else:
            st.error("❌ PING FAILED.")

    garden_data = get_data()
    st.metric("Plants in Cloud", len(garden_data))
    
    if st.button("🔄 REFRESH GALLERY"): st.rerun()
    
    st.divider()
    st.subheader("🚀 Migration")
    uploaded_json = st.file_uploader("Upload JSON", type="json")
    if uploaded_json and st.button("Start Moving"):
        data_list = json.load(uploaded_json)
        prog = st.progress(0)
        for i, p in enumerate(data_list):
            p_name = p.get('name', 'Plant').replace("**", "")
            img = p.get('image') or (p['history'][-1].get('image') if 'history' in p else "")
            # Shrink images to absolute minimum for migration
            if img:
                try:
                    decoded = base64.b64decode(img)
                    temp_img = Image.open(io.BytesIO(decoded))
                    buf = io.BytesIO()
                    temp_img.save(buf, format="JPEG", quality=10)
                    img = base64.b64encode(buf.getvalue()).decode('utf-8')
                except: img = ""
            save_to_cloud(p_name, p.get('location', 'Lounge'), img, p.get('data', ''))
            prog.progress((i + 1) / len(data_list))
        st.rerun()

    st.divider()
    st.header("📸 Add New")
    pic = st.file_uploader("Take Photo", type=['jpg', 'jpeg', 'png', 'HEIC', 'heic'])
    loc_in = st.text_input("Room")
    if st.button("SAVE PLANT"):
        if pic:
            with st.spinner("AI Analysis..."):
                genai.configure(api_key=G_KEY)
                model = genai.GenerativeModel('gemini-1.5-flash')
                img_obj = Image.open(pic).convert('RGB')
                response = model.generate_content(["Identify this plant and give care tips.", img_obj])
                
                # Compress photo
                buf = io.BytesIO()
                img_obj.save(buf, format="JPEG", quality=30)
                img_b64 = base64.b64encode(buf.getvalue()).decode('utf-8')
                
                if save_to_cloud("New Plant", loc_in, img_b64, response.text):
                    st.success("Saved!")
                    st.rerun()

# 6. GALLERY DISPLAY
if st.session_state.get('view_mode') != 'details':
    st.title("My Garden")
    cols = st.columns(2)
    for i, plant in enumerate(reversed(garden_data)):
        if plant['name'] != "Connection Test":
            with cols[i % 2]:
                st.markdown('<div class="gallery-card">', unsafe_allow_html=True)
                if plant['image']: st.image(base64.b64decode(plant['image']), use_container_width=True)
                st.subheader(plant['name'])
                st.write(f"📍 {plant['location']}")
                if st.button("DETAILS", key=f"v_{plant['id']}"):
                    st.session_state.selected_plant = plant
                    st.session_state.view_mode = 'details'
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)
else:
    # DETAIL VIEW
    p = st.session_state.selected_plant
    if st.button("⬅️ BACK"):
        st.session_state.view_mode = 'gallery'
        st.rerun()
    st.header(p['name'])
    st.image(base64.b64decode(p['image']), use_container_width=True)
    st.info(p['data'])
