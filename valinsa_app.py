import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import re
from datetime import datetime

# --- 1. KONFIGURASI HALAMAN ---
st.set_page_config(
    page_title="VALINSA Cloud - Telkom Infrastructure",
    page_icon="🔴",
    layout="centered"
)

# --- 2. KONEKSI GOOGLE SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)

# --- 3. CUSTOM CSS (FIX CONTRAST & UI) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .stApp { background: linear-gradient(180deg, #ffffff 0%, #f9f9f9 100%); }
    input[type="text"], .stTextArea textarea {
        color: #000000 !important;
        background-color: #ffffff !important;
        -webkit-text-fill-color: #000000 !important;
    }
    .input-card {
        background-color: white; padding: 30px; border-radius: 15px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.05); border-top: 5px solid #EE2D24;
        margin-bottom: 20px;
    }
    .stButton>button {
        width: 100%; background: linear-gradient(90deg, #EE2D24 0%, #ff4d4d 100%);
        color: white !important; border-radius: 10px; height: 3.8em; font-weight: 800; border: none;
    }
    [data-testid="stSidebar"] { background-color: #1a1a1a; }
    [data-testid="stSidebar"] .stTextInput input { color: #000000 !important; background-color: #ffffff !important; }
    [data-testid="stSidebar"] * { color: white !important; }
    .footer { text-align: center; padding: 20px; font-size: 0.8em; color: #666; margin-top: 50px; border-top: 1px solid #eee; }
    </style>
    """, unsafe_allow_html=True)

# --- 4. SIDEBAR ---
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/id/thumb/c/c4/Telkom_Infrastructure.svg/1200px-Telkom_Infrastructure.svg.png")
    st.markdown("### 🛠️ System Settings")
    user_input = st.text_input("👤 Nama Penginput:", placeholder="Ketikkan nama disini...")
    st.success("● Cloud Sync Active")
    st.write("---")
    # Nama tab disesuaikan menjadi FollowUP
    target_sheet = "FollowUP"
    st.caption(f"Target Worksheet: {target_sheet}")

# --- 5. HEADER ---
st.markdown("""
    <div style='text-align: center; margin-bottom: 20px;'>
        <h1 style='font-size: 3em; margin-bottom: 0; color: #EE2D24;'>VALINSA CLOUD</h1>
        <p style='color: #666;'>VALINS Automation System by Student Internship Telkom Gaharu 2026</p>
    </div>
    """, unsafe_allow_html=True)

# --- 6. LOGIKA INPUT ---
st.markdown('<div class="input-card">', unsafe_allow_html=True)
st.write(f"##### 📝 Paste Data Mentah (Oleh: {user_input if user_input else '...' })")
raw_input = st.text_area(label="Input Data", height=250, placeholder="Tempel data disini...", label_visibility="collapsed")
st.markdown('</div>', unsafe_allow_html=True)

if st.button("🚀 EKSEKUSI CLOUD SYNC"):
    if not user_input.strip():
        st.error("⚠️ Isi Nama Penginput di sidebar!")
    elif not raw_input.strip():
        st.warning("⚠️ Input data kosong!")
    else:
        try:
            # 1. BACA DATA
            try:
                df_existing = conn.read(worksheet=target_sheet, ttl=0)
            except Exception:
                df_existing = pd.DataFrame()

            # Tentukan Header Standar jika sheet kosong (A sampai K)
            headers = ["Tanggal", "STO", "Nama ODP", "Panel", "ID Valins", "Cek RAM", "ID Barcode", "Status IXSA", "Keterangan", "List RED", "Inputed By"]
            
            if df_existing.empty:
                df_existing = pd.DataFrame(columns=headers)
                existing_ids = []
            else:
                # Pastikan jumlah kolom minimal 5 untuk ambil ID Valins di kolom E
                if len(df_existing.columns) >= 5:
                    existing_ids = df_existing.iloc[:, 4].astype(str).str.strip().tolist()
                else:
                    existing_ids = []

            num_cols = len(df_existing.columns)

            # 2. EKSTRAKSI DATA
            odp_list = re.findall(r'(ODP-[\w/-]+)', raw_input)
            panel_list = re.findall(r'PANEL\s*[:\-]?\s*(\d+)', raw_input, re.IGNORECASE)
            valins_list = re.findall(r'(?:VALINS\s*(?:ID)?\s*[:\-]?\s*)?(\d{8})', raw_input, re.IGNORECASE)

            count = min(len(odp_list), len(panel_list), len(valins_list))
            data_to_append = []
            duplicates = []
            
            for i in range(count):
                v_id = valins_list[i].strip()
                o_name = odp_list[i].strip()
                p_label = f"PANEL {panel_list[i].strip()}"
                sto_val = o_name.split('-')[1].upper() if '-' in o_name else ""
                
                if v_id in existing_ids:
                    duplicates.append({"ODP": o_name, "ID": v_id})
                else:
                    # Buat baris data baru sesuai jumlah kolom di spreadsheet
                    new_row = [""] * num_cols
                    new_row[0] = datetime.now().strftime("%Y-%m-%d")    # A. Tanggal
                    new_row[1] = sto_val                                # B. STO
                    new_row[2] = o_name                                 # C. Nama ODP
                    new_row[3] = p_label                                # D. Panel
                    new_row[4] = v_id                                   # E. ID Valins
                    
                    if num_cols >= 8:
                        new_row[7] = "Pending"                          # H. Status IXSA
                    if num_cols >= 11:
                        new_row[10] = f"VALINSA - {user_input}"         # K. Inputed By
                    
                    data_to_append.append(new_row)
                    existing_ids.append(v_id)

            # 3. UPDATE DATA
            if data_to_append:
                df_new = pd.DataFrame(data_to_append, columns=df_existing.columns)
                df_final = pd.concat([df_existing, df_new], ignore_index=True)
                
                # Membersihkan data dari null/NaN (Penyebab utama Error 400)
                df_final = df_final.fillna("").astype(str)
                
                # Kirim balik ke Google Sheets
                conn.update(worksheet=target_sheet, data=df_final)
                
                st.balloons()
                st.success(f"✅ Berhasil sinkron ke '{target_sheet}'")
                st.dataframe(df_new.iloc[:, [0, 1, 2, 3, 4]]) 
            else:
                st.info("ℹ️ Tidak ada data baru (duplikat diabaikan).")

            if duplicates:
                st.warning(f"⚠️ {len(duplicates)} data duplikat ditolak.")
                st.table(pd.DataFrame(duplicates))

        except Exception as e:
            st.error(f"🚨 Terjadi Kesalahan Cloud: {e}")
            st.info(f"Pastikan tab di Google Sheets benar-benar bernama '{target_sheet}' (Tanpa Spasi)")

st.markdown("""<div class="footer"><b>PT TELKOM INFRASTRUKTUR INDONESIA</b><br>Regional Medan Gaharu</div>""", unsafe_allow_html=True)