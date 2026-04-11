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
    st.error("Setup incomplete. Check Streamlit Secrets.")
    st.stop()

# 3. ABSOLUTE HIGH-CONTRAST STYLING (Forced for Mobile)
st.markdown("""
    <style>
    /* 1. Global Background - Forced Pure Black */
    .stApp, [data-testid="stSidebar"], [data-testid="stHeader"], .main {
        background-color: #000000 !important;
    }

    /* 2. Global Text - Forced Pure White */
    p, li, h1, h2, h3, span, label, div, .stMarkdown, .stCaption {
        color: #FFFFFF !important;
        font-weight: 500 !important;
    }

    /* 3. Sidebar Specific - Kill the Gray */
    section[data-testid="stSidebar"] {
        background-color: #000000 !important;
        border-right: 1px solid #333333;
    }

    /* 4. Gallery Cards - Black with White Border */
    .gallery-card {
        background-color: #111111 !important;
        padding: 15px;
        border-radius: 15px;
        border: 2px solid #FFFFFF !important; /* White border for high contrast */
        text-align: center;
        margin-bottom: 25px;
    }

    /* 5. Dashboard Boxes - Solid Black Backgrounds */
    .box {
        padding: 20px;
        border-radius: 12px;
        margin-bottom: 20px;
        border: 4px solid !important;
        background-color: #000000 !important;
    }
    .box-flourish { border-color: #22C55E !important; }
    .box-forbidden { border-color: #EF4444 !important; }
    .box-prune { border-color: #3B82F6 !important; }
    .box-glorious { border-color: #FACC15 !important; }
    
    .header-label {
        font-weight: 900 !important;
        color: #FFFFFF !important;
        font-size: 1.3rem !important;
        text-transform: uppercase;
        display: block;
        margin-bottom: 8px;
    }

    /* 6. Buttons - Forced High Contrast */
    button {
        background-color: #FFFFFF !important;
        color: #000000 !important;
        font-weight: bold !important;
        border-radius: 8px !important;
        border: none !important;
    }

    /* 7. Input Fields - Dark with White Text */
    input, textarea, [data-testid="stFileUploadDropzone"] {
        background-color: #222222 !important;
        color: #FFFFFF !important;
        border: 1px solid #FFFFFF !important;
    }
    
    /* 8. Fix for Expander (Pruning Map) */
    details {
        background-color: #111111 !important;
        border: 1px solid #FFFFFF !important;
        border-radius: 8px;
    }
    </style>
    """, unsafe_allow_html=True)

# 4. HELPERS
def get_sec(text, sec):
    try:
        parts = text.split(f"[{sec}]")
        return parts[1].split("[")[0].strip() if len(parts) > 1 else "Processing..."
    except: return "Section error."

# 5. SIDEBAR
with st.sidebar:
    st.title("🌿 Peter's Garden")
    if st.button("🔄 REFRESH"): st.rerun()
    
    st.divider()
    st.header("📸 New Plant")
    pic = st.file_uploader("Upload/Take Photo", type=['jpg', 'jpeg', 'png', 'HEIC', 'heic'])
    loc_in = st.text_input("Which Room?")
    
    if st.button("SAVE TO CLOUD") and pic:
        with st.spinner("AI analyzing..."):
            genai.configure(api_key=G_KEY)
            model = genai.GenerativeModel('gemini-1.5-flash')
            img_obj = Image.open(pic).convert('RGB')
            prompt = "Identify this plant and provide: [NAME], [FLOURISH], [FORBIDDEN], [PRUNE_FEED], [GLORIOUS], [PRIME], and [MAP]."
            response = model.generate_content([prompt, img_obj])
            ai_text = response.text
            
            buf = io.BytesIO()
            img_obj.save(buf, format="JPEG", quality=40)
            img_b64 = base64.b64encode(buf.getvalue()).decode('utf-8')
            
            p_name = get_sec(ai_text, "NAME")
            supabase.table("garden_table").insert({
                "name": p_name, "location": loc_in, "image": img_b64, "data": ai_text
            }).execute()
            st.success(f"Saved {p_name}!")
            st.rerun()

# 6. MAIN DISPLAY
garden_data = supabase.table("garden_table").select("*").execute().data

if st.session_state.get('view_mode') != 'details':
    st.title("My Gallery")
    # Force 2 columns on iPad/iPhone for big, readable photos
    cols = st.columns(2)
    for i, plant in enumerate(reversed(garden_data)):
        with cols[i % 2]:
            st.markdown('<div class="gallery-card">', unsafe_allow_html=True)
            if plant['image']: 
                st.image(base64.b64decode(plant['image']), use_container_width=True)
            st.subheader(plant['name'])
            st.write(f"📍 {plant['location']}")
            if st.button("VIEW DETAILS", key=f"v_{plant['id']}"):
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
    st.image(base64.b64decode(p['image']), use_container_width=True)
    st.markdown(f'<div class="box" style="border-color:#1E3A8A;"><span class="header-label">📍 LOCATION</span>{p["location"]}</div>', unsafe_allow_html=True)

    # Dashboard Boxes
    st.markdown(f'<div class="box box-flourish"><span class="header-label">🌿 To Flourish</span>{get_sec(p["data"], "FLOURISH")}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="box box-forbidden"><span class="header-label">🚫 Forbidden</span>{get_sec(p["data"], "FORBIDDEN")}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="box box-prune"><span class="header-label">✂️ Prune & Feed</span>{get_sec(p["data"], "PRUNE_FEED")}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="box box-glorious"><span class="header-label">✨ Glorious Tips</span>{get_sec(p["data"], "GLORIOUS")}</div>', unsafe_allow_html=True)
    
    with st.expander("📍 VIEW PRUNING MAP"):
        st.write(get_sec(p['data'], 'MAP'))
    
    if st.button("🗑️ DELETE FROM DATABASE"):
        supabase.table("garden_table").delete().eq("id", p['id']).execute()
        st.session_state.view_mode = 'gallery'
        st.rerun()
