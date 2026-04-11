import streamlit as st
import google.generativeai as genai
import base64
import json
from PIL import Image
import io
from supabase import create_client, Client

# 1. PAGE SETUP
st.set_page_config(page_title="Peter's Garden", layout="wide", page_icon="🌿")

# 2. CLOUD CONNECTION
try:
    URL = st.secrets["SB_URL"].strip()
    KEY = st.secrets["SB_KEY"].strip()
    G_KEY = st.secrets["GEMINI_KEY"].strip()
    supabase: Client = create_client(URL, KEY)
except Exception as e:
    st.error("Setup incomplete. Check Streamlit Secrets.")
    st.stop()

# 3. NUCLEAR CONTRAST STYLING (Forced for iPad/iPhone)
st.markdown("""
    <style>
    /* Force Background to Pure Black */
    .stApp, [data-testid="stSidebar"], [data-testid="stHeader"] {
        background-color: #000000 !important;
    }

    /* Force ALL text to White by default */
    h1, h2, h3, p, li, span, label, div {
        color: #FFFFFF !important;
    }

    /* Target the Sidebar specifically to kill Gray */
    [data-testid="stSidebar"] section {
        background-color: #000000 !important;
    }

    /* INPUT FIELDS (The "Which Room?" boxes) */
    input, textarea {
        background-color: #111111 !important;
        color: #FFFFFF !important;
        border: 2px solid #FFFFFF !important;
        border-radius: 5px !important;
    }

    /* FILE UPLOADER (The "White Box" fix) */
    /* We make it dark gray so the white text "Drag and Drop" is visible */
    [data-testid="stFileUploadDropzone"] {
        background-color: #222222 !important;
        border: 2px dashed #FFFFFF !important;
        color: #FFFFFF !important;
    }
    [data-testid="stFileUploadDropzone"] div, [data-testid="stFileUploadDropzone"] small {
        color: #FFFFFF !important;
    }

    /* BUTTONS - Black text on White background for extreme visibility */
    button, [data-testid="stBaseButton-secondary"] {
        background-color: #FFFFFF !important;
        color: #000000 !important;
        border: 2px solid #FFFFFF !important;
        font-weight: 900 !important;
        text-transform: uppercase !important;
    }

    /* DASHBOARD BOXES */
    .box {
        padding: 20px;
        border-radius: 12px;
        margin-bottom: 20px;
        border: 5px solid !important;
        background-color: #000000 !important;
    }
    .box-flourish { border-color: #22C55E !important; }
    .box-forbidden { border-color: #EF4444 !important; }
    .box-prune { border-color: #3B82F6 !important; }
    .box-glorious { border-color: #FACC15 !important; }
    
    .header-label {
        font-weight: 900 !important;
        color: #FFFFFF !important;
        font-size: 1.4rem !important;
        text-transform: uppercase;
        display: block;
        margin-bottom: 8px;
    }

    /* GALLERY CARDS */
    .gallery-card {
        background-color: #111111 !important;
        padding: 15px;
        border-radius: 15px;
        border: 2px solid #FFFFFF !important;
        text-align: center;
        margin-bottom: 25px;
    }
    
    /* Fix for Expander/Pruning Map */
    details {
        border: 2px solid #FFFFFF !important;
        background-color: #111111 !important;
        color: #FFFFFF !important;
    }
    </style>
    """, unsafe_allow_html=True)

# 4. HELPERS
def get_sec(text, sec):
    try:
        parts = text.split(f"[{sec}]")
        return parts[1].split("[")[0].strip() if len(parts) > 1 else "..."
    except: return "Error."

# 5. SIDEBAR
with st.sidebar:
    st.markdown("### 🌿 Peter's Garden")
    if st.button("🔄 REFRESH GALLERY"): st.rerun()
    
    st.divider()
    st.markdown("### 📸 New Plant")
    pic = st.file_uploader("Upload/Take Photo", type=['jpg', 'jpeg', 'png', 'HEIC', 'heic'])
    loc_in = st.text_input("Which Room?")
    
    if st.button("SAVE TO CLOUD") and pic:
        with st.spinner("Analyzing..."):
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
            st.success(f"Saved!")
            st.rerun()

# 6. MAIN DISPLAY
res = supabase.table("garden_table").select("*").execute()
garden_data = res.data

if st.session_state.get('view_mode') != 'details':
    st.markdown("## My Gallery")
    cols = st.columns(2)
    for i, plant in enumerate(reversed(garden_data)):
        with cols[i % 2]:
            st.markdown('<div class="gallery-card">', unsafe_allow_html=True)
            if plant['image']: 
                st.image(base64.b64decode(plant['image']), use_container_width=True)
            st.markdown(f"### {plant['name']}")
            st.markdown(f"📍 {plant['location']}")
            if st.button("DETAILS", key=f"v_{plant['id']}"):
                st.session_state.selected_plant = plant
                st.session_state.view_mode = 'details'
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
else:
    # 7. DETAIL VIEW
    p = st.session_state.selected_plant
    if st.button("⬅️ BACK"):
        st.session_state.view_mode = 'gallery'
        st.rerun()
        
    st.markdown(f"# {p['name']}")
    st.image(base64.b64decode(p['image']), use_container_width=True)
    st.markdown(f"📍 **LOCATION:** {p['location']}")

    st.markdown(f'<div class="box box-flourish"><span class="header-label">🌿 To Flourish</span>{get_sec(p["data"], "FLOURISH")}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="box box-forbidden"><span class="header-label">🚫 Forbidden</span>{get_sec(p["data"], "FORBIDDEN")}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="box box-prune"><span class="header-label">✂️ Prune & Feed</span>{get_sec(p["data"], "PRUNE_FEED")}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="box box-glorious"><span class="header-label">✨ Glorious Tips</span>{get_sec(p["data"], "GLORIOUS")}</div>', unsafe_allow_html=True)
    
    with st.expander("📍 VIEW PRUNING MAP"):
        st.write(get_sec(p['data'], 'MAP'))
    
    if st.button("🗑️ DELETE"):
        supabase.table("garden_table").delete().eq("id", p['id']).execute()
        st.session_state.view_mode = 'gallery'
        st.rerun()
