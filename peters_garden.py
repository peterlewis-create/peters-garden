import streamlit as st
import google.generativeai as genai
import base64
import json
from PIL import Image
import io
from supabase import create_client, Client

# 1. PAGE SETUP
st.set_page_config(page_title="Peter's Garden", layout="wide", page_icon="🌿")

# 2. CLOUD CONNECTION (Secrets)
try:
    URL = st.secrets["SB_URL"].strip()
    KEY = st.secrets["SB_KEY"].strip()
    G_KEY = st.secrets["GEMINI_KEY"].strip()
    supabase: Client = create_client(URL, KEY)
except Exception as e:
    st.error("Setup incomplete. Please add SB_URL, SB_KEY, and GEMINI_KEY to Streamlit Secrets.")
    st.stop()

# 3. STYLING (High Contrast Peter's Garden Theme)
st.markdown("""
    <style>
    .stApp { background-color: #000000 !important; }
    p, li, h1, h2, h3, span, label, div, .stMarkdown { color: #FFFFFF !important; }
    .gallery-card { background-color: #111111; padding: 15px; border-radius: 15px; border: 1px solid #333; text-align: center; margin-bottom: 20px; }
    .box { padding: 15px; border-radius: 10px; margin-bottom: 15px; border: 2px solid; background-color: #000; }
    .box-flourish { border-color: #22C55E; }
    .box-forbidden { border-color: #EF4444; }
    .box-prune { border-color: #3B82F6; }
    .box-glorious { border-color: #FACC15; }
    .header-label { font-weight: 900; color: #FFFFFF; font-size: 1.1rem; text-transform: uppercase; display: block; margin-bottom: 5px; }
    </style>
    """, unsafe_allow_html=True)

# 4. HELPERS
def get_sec(text, sec):
    try:
        parts = text.split(f"[{sec}]")
        return parts[1].split("[")[0].strip() if len(parts) > 1 else "Data pending..."
    except: return "Error reading section."

def save_to_cloud(name, loc, img, info):
    supabase.table("garden_table").insert({
        "name": str(name), "location": str(loc), "image": str(img), "data": str(info)
    }).execute()

# 5. SIDEBAR
with st.sidebar:
    st.title("🌿 Peter's Garden")
    if st.button("🔄 REFRESH SYNC"): st.rerun()
    
    st.divider()
    st.header("📸 Add New Plant")
    pic = st.file_uploader("Take/Upload Photo", type=['jpg', 'jpeg', 'png', 'HEIC', 'heic'])
    loc_in = st.text_input("Which Room?")
    
    if st.button("IDENTIFY & SAVE") and pic:
        with st.spinner("AI is analyzing..."):
            genai.configure(api_key=G_KEY)
            model = genai.GenerativeModel('gemini-1.5-flash')
            img_obj = Image.open(pic).convert('RGB')
            
            prompt = "Identify this plant and provide: [NAME], [FLOURISH], [FORBIDDEN], [PRUNE_FEED], [GLORIOUS], [PRIME], and [MAP]."
            response = model.generate_content([prompt, img_obj])
            ai_text = response.text
            
            # Compress and Save
            buf = io.BytesIO()
            img_obj.save(buf, format="JPEG", quality=40)
            img_b64 = base64.b64encode(buf.getvalue()).decode('utf-8')
            
            p_name = get_sec(ai_text, "NAME")
            save_to_cloud(p_name, loc_in, img_b64, ai_text)
            st.success(f"Saved {p_name} to Cloud!")
            st.rerun()

# 6. MAIN DISPLAY
garden_data = supabase.table("garden_table").select("*").execute().data

if st.session_state.get('view_mode') != 'details':
    st.title("My Garden")
    # 2 columns for mobile, 3-4 for laptop
    cols = st.columns(2 if st.sidebar.checkbox("Mobile View", True) else 4)
    for i, plant in enumerate(reversed(garden_data)):
        with cols[i % len(cols)]:
            st.markdown('<div class="gallery-card">', unsafe_allow_html=True)
            if plant['image']: 
                st.image(base64.b64decode(plant['image']), use_container_width=True)
            st.subheader(plant['name'])
            st.caption(f"📍 {plant['location']}")
            if st.button("DETAILS", key=f"v_{plant['id']}"):
                st.session_state.selected_plant = plant
                st.session_state.view_mode = 'details'
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
else:
    # 7. DETAIL VIEW (The High-Contrast Dashboard)
    p = st.session_state.selected_plant
    if st.button("⬅️ BACK TO GALLERY"):
        st.session_state.view_mode = 'gallery'
        st.rerun()
        
    st.header(p['name'])
    col_l, col_r = st.columns([1, 1.5])
    
    with col_l:
        st.image(base64.b64decode(p['image']), use_container_width=True)
        st.markdown(f"**📍 Location:** {p['location']}")
        st.divider()
        st.subheader("🌟 IN ITS PRIME")
        st.write(get_sec(p['data'], 'PRIME'))
        if st.button("🗑️ DELETE PLANT"):
            supabase.table("garden_table").delete().eq("id", p['id']).execute()
            st.session_state.view_mode = 'gallery'
            st.rerun()

    with col_r:
        # THE BOXES
        st.markdown(f'<div class="box box-flourish"><span class="header-label">🌿 To Flourish</span>{get_sec(p["data"], "FLOURISH")}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="box box-forbidden"><span class="header-label">🚫 Forbidden</span>{get_sec(p["data"], "FORBIDDEN")}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="box box-prune"><span class="header-label">✂️ Prune & Feed</span>{get_sec(p["data"], "PRUNE_FEED")}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="box box-glorious"><span class="header-label">✨ Glorious Tips</span>{get_sec(p["data"], "GLORIOUS")}</div>', unsafe_allow_html=True)
        
        with st.expander("📍 VIEW PRUNING MAP (What to cut right now)"):
            st.warning(get_sec(p['data'], 'MAP'))
