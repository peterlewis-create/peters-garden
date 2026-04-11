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

# 3. SOPHISTICATED GARDEN STYLING (Slate, Sage & Soft White)
st.markdown("""
    <style>
    /* 1. Global Background - Deep Slate Navy */
    .stApp, [data-testid="stSidebar"], [data-testid="stHeader"] {
        background-color: #0F172A !important;
    }

    /* 2. Global Text - Soft Off-White */
    h1, h2, h3, p, li, span, label, div, .stMarkdown {
        color: #F1F5F9 !important;
        font-family: 'Inter', sans-serif;
    }

    /* 3. Sidebar - Slightly Lighter Slate */
    [data-testid="stSidebar"] {
        background-color: #1E293B !important;
        border-right: 2px solid #334155;
    }

    /* 4. Input Fields - Explicit Colors to prevent "Ghosting" */
    input, textarea {
        background-color: #0F172A !important;
        color: #FFFFFF !important;
        border: 2px solid #475569 !important;
    }

    /* 5. File Uploader - Sage Green Border */
    [data-testid="stFileUploadDropzone"] {
        background-color: #1E293B !important;
        border: 2px dashed #22C55E !important;
        color: #F1F5F9 !important;
    }

    /* 6. Buttons - Sage Green with Dark Text */
    button, [data-testid="stBaseButton-secondary"] {
        background-color: #22C55E !important;
        color: #0F172A !important;
        border: none !important;
        font-weight: 700 !important;
        padding: 10px 20px !important;
        border-radius: 8px !important;
    }

    /* 7. Gallery Cards - Clean Slate */
    .gallery-card {
        background-color: #1E293B !important;
        padding: 15px;
        border-radius: 16px;
        border: 1px solid #334155;
        text-align: center;
        margin-bottom: 25px;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.3);
    }

    /* 8. Dashboard Boxes - Professional Colored Fills */
    .box {
        padding: 20px;
        border-radius: 12px;
        margin-bottom: 20px;
        color: #FFFFFF !important;
        border-left: 10px solid !important;
    }
    .box-flourish { background-color: #064E3B; border-color: #22C55E !important; } /* Deep Green */
    .box-forbidden { background-color: #450A0A; border-color: #EF4444 !important; } /* Deep Red */
    .box-prune { background-color: #1E3A8A; border-color: #3B82F6 !important; }     /* Deep Blue */
    .box-glorious { background-color: #422006; border-color: #F59E0B !important; }  /* Deep Gold */
    
    .header-label {
        font-weight: 800 !important;
        color: #F1F5F9 !important;
        font-size: 1.2rem !important;
        text-transform: uppercase;
        letter-spacing: 1px;
        display: block;
        margin-bottom: 5px;
    }

    /* Fix for Expander */
    details {
        background-color: #1E293B !important;
        border: 1px solid #334155 !important;
        border-radius: 8px;
        padding: 10px;
    }
    summary { font-weight: bold; color: #22C55E !important; }
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
    if st.button("🔄 REFRESH SYSTEM"): st.rerun()
    
    st.divider()
    st.markdown("#### 📸 New Entry")
    pic = st.file_uploader("Capture Photo", type=['jpg', 'jpeg', 'png', 'HEIC', 'heic'])
    loc_in = st.text_input("Assign Room")
    
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
            st.success(f"Saved!")
            st.rerun()

# 6. MAIN DISPLAY
res = supabase.table("garden_table").select("*").execute()
garden_data = res.data

if st.session_state.get('view_mode') != 'details':
    st.markdown("## My Garden Collection")
    cols = st.columns(2)
    for i, plant in enumerate(reversed(garden_data)):
        with cols[i % 2]:
            st.markdown('<div class="gallery-card">', unsafe_allow_html=True)
            if plant['image']: 
                st.image(base64.b64decode(plant['image']), use_container_width=True)
            st.markdown(f"### {plant['name']}")
            st.markdown(f"📍 {plant['location']}")
            if st.button("OPEN DASHBOARD", key=f"v_{plant['id']}"):
                st.session_state.selected_plant = plant
                st.session_state.view_mode = 'details'
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
else:
    # 7. DETAIL VIEW
    p = st.session_state.selected_plant
    if st.button("⬅️ RETURN TO GALLERY"):
        st.session_state.view_mode = 'gallery'
        st.rerun()
        
    st.markdown(f"# {p['name']}")
    col_l, col_r = st.columns([1, 1]) # Balanced for iPad
    
    with col_l:
        st.image(base64.b64decode(p['image']), use_container_width=True)
        st.markdown(f"### 📍 LOCATION: {p['location']}")
        st.divider()
        st.markdown("#### 🌟 GOAL: IN ITS PRIME")
        st.write(get_sec(p['data'], 'PRIME'))

    with col_r:
        # THE BOXES (Color Filled with White Text)
        st.markdown(f'<div class="box box-flourish"><span class="header-label">🌿 To Flourish</span>{get_sec(p["data"], "FLOURISH")}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="box box-forbidden"><span class="header-label">🚫 Forbidden</span>{get_sec(p["data"], "FORBIDDEN")}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="box box-prune"><span class="header-label">✂️ Prune & Feed</span>{get_sec(p["data"], "PRUNE_FEED")}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="box box-glorious"><span class="header-label">✨ Glorious Tips</span>{get_sec(p["data"], "GLORIOUS")}</div>', unsafe_allow_html=True)
        
        with st.expander("📍 VIEW PRUNING MAP"):
            st.write(get_sec(p['data'], 'MAP'))
    
    st.divider()
    if st.button("🗑️ REMOVE PLANT"):
        supabase.table("garden_table").delete().eq("id", p['id']).execute()
        st.session_state.view_mode = 'gallery'
        st.rerun()
