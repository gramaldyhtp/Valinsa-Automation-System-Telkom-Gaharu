import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import re
from datetime import datetime
import time

# --- 1. INITIAL CONFIG (Tampilan Wide) ---
st.set_page_config(
    page_title="VALINSA Cloud Sync", 
    page_icon="🔴", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. SETUP & CONFIGURATION ---
def get_connection():
    """Mengambil koneksi Google Sheets dengan caching."""
    return st.connection("gsheets", type=GSheetsConnection)

try:
    S_ID = st.secrets["connections"]["gsheets"]["spreadsheet_id"]
    SHEET_NAME = "FollowUP" 
    HAS_CONFIG = True
except Exception:
    HAS_CONFIG = False

# --- 3. UI DESIGN ---
st.markdown(
    "<h1 style='text-align: center; color: #EE2D24;'>VALINSA CLOUD SYNC</h1>", 
    unsafe_allow_html=True
)
st.markdown(
    "<p style='text-align: center; color: #555;'>Sistem Otomatisasi Data Infrastruktur - Telkom Infrastruktur Indonesia</p>", 
    unsafe_allow_html=True
)

# Sidebar
with st.sidebar:
    st.image(
        "https://upload.wikimedia.org/wikipedia/commons/thumb/6/6f/Telkom_Indonesia_logo.svg/1200px-Telkom_Indonesia_logo.svg.png", 
        use_container_width=True
    )
    st.subheader("⚙️ Konfigurasi")
    
    if not HAS_CONFIG:
        st.error("⚠️ **Setup Belum Lengkap!**")
        st.info("Pastikan ID Spreadsheet sudah benar di Secrets.")
        st.stop()
    
    st.divider()
    st.subheader("Profil Penginput")
    user_name = st.text_input(
        "👤 Nama ():", 
        placeholder="Masukkan nama...",
        key="user_input"
    )
    
    st.divider()
    if st.button("🧹 Clear System Cache", type="secondary"):
        with st.spinner("Membersihkan cache..."):
            st.cache_data.clear()
            st.cache_resource.clear()
            st.success("Cache dibersihkan! Silakan refresh.")

# --- 4. TEST KONEKSI GOOGLE SHEETS ---
st.subheader("🔗 Status Koneksi")
conn_status = "unknown"
conn_data = None

try:
    test_conn = get_connection()
    test_data = test_conn.read(spreadsheet=S_ID, worksheet=SHEET_NAME, ttl=0)
    conn_status = "success"
    conn_data = test_data
except Exception as e:
    conn_status = "error"
    conn_message = f"❌ Koneksi Gagal: {str(e)}"

if conn_status == "success":
    st.success("✅ Koneksi Google Sheets Berhasil!")
    if conn_data is not None and not conn_data.empty:
        st.write(f"📊 Total baris di sheet: {len(conn_data)}")
else:
    st.error(conn_message)

# --- 5. INPUT AREA ---
st.subheader("📋 Input Data Lapangan")
raw_input = st.text_area(
    "Paste Data di sini:", 
    height=200, 
    placeholder="Contoh:\nODP-LGB-FA/01 PANEL: 1 VALINS: 12345678",
    key="raw_data"
)

# --- 6. PREVIEW & VALIDASI ---
preview_df = None
if raw_input and user_name:
    with st.spinner("Menganalisis data..."):
        try:
            odps = re.findall(r'(ODP-[\w\-/]+)', raw_input.upper())
            panels = re.findall(r'PANEL\s*[:\-]?\s*(\d+)', raw_input.upper())
            valins_ids = re.findall(r'(?:VALINS|ID)?\s*[:\-]?\s*(\d{7,10})', raw_input.upper())
            
            count = min(len(odps), len(valins_ids))
            
            if count > 0:
                new_entries = []
                for i in range(count):
                    v_id = valins_ids[i].strip()
                    sto_code = odps[i].split('-')[1] if '-' in odps[i] else ""
                    new_entries.append({
                        "Tanggal": datetime.now().strftime("%Y-%m-%d"),
                        "STO": sto_code,
                        "NamaODP": odps[i],
                        "Panel": f"PANEL {panels[i]}" if i < len(panels) else "",
                        "ID Valins": v_id,
                        "ID Valins FU": "",
                        "Status IXSA": "Pending",
                        "Keterangan IXSA": "",
                        "List ODP RED": "",
                        "Inputed By": f"VALINSA - {user_name}"
                    })
                preview_df = pd.DataFrame(new_entries)
                st.success(f"✅ Terdeteksi {count} data valid.")
                with st.expander("🔍 Lihat Preview Data"):
                    st.dataframe(preview_df, use_container_width=True)
            else:
                st.warning("⚠️ Data tidak terdeteksi.")
        except Exception as e:
            st.error(f"❌ Error saat analisis: {e}")

# --- 7. LOGIKA EKSEKUSI (Update Spreadsheet & Deteksi Duplikat Ketat) ---
if preview_df is not None and st.button("🚀 SINRONISASI KE CLOUD", type="primary", use_container_width=True):
    try:
        conn = get_connection()
        with st.spinner("⏳ Memeriksa duplikat dan mengirim data..."):
            df_existing = conn.read(spreadsheet=S_ID, worksheet=SHEET_NAME, ttl=0)
            
            existing_ids_set = set()
            
            if df_existing is not None and not df_existing.empty:
                df_existing = df_existing.dropna(how='all')
                if "ID Valins" in df_existing.columns:
                    # NORMALISASI KETAT: 
                    # 1. Ubah ke string
                    # 2. Hapus desimal '.0' yang sering muncul dari Google Sheets
                    # 3. Hapus spasi
                    existing_ids_set = set(
                        df_existing["ID Valins"].astype(str)
                        .str.replace(r'\.0$', '', regex=True)
                        .str.strip()
                        .tolist()
                    )

            new_rows_to_add = []
            duplicate_ids_found = []
            
            for _, row in preview_df.iterrows():
                # Normalisasi ID input
                current_id = str(row["ID Valins"]).strip()
                
                if current_id in existing_ids_set:
                    duplicate_ids_found.append(current_id)
                else:
                    new_rows_to_add.append(row)
                    existing_ids_set.add(current_id)
            
            if not new_rows_to_add:
                st.warning(f"🚫 **Gagal:** Semua data ({len(duplicate_ids_found)} ID) sudah ada di database.")
                if duplicate_ids_found:
                    st.info(f"ID Duplikat: {', '.join(set(duplicate_ids_found))}")
            else:
                df_new_to_push = pd.DataFrame(new_rows_to_add)
                
                if df_existing is not None and not df_existing.empty:
                    df_final = pd.concat([df_existing, df_new_to_push], ignore_index=True)
                else:
                    df_final = df_new_to_push
                
                # Pastikan data dikirim sebagai string murni untuk mencegah munculnya kembali desimal .0
                df_final = df_final.fillna("").astype(str)
                
                conn.update(spreadsheet=S_ID, worksheet=SHEET_NAME, data=df_final)
                
                st.balloons()
                st.success(f"✅ **Berhasil!** {len(new_rows_to_add)} data baru ditambahkan.")
                
                if duplicate_ids_found:
                    st.warning(f"⚠️ {len(set(duplicate_ids_found))} data lainnya diabaikan karena duplikat.")
                
                time.sleep(2)
                st.rerun()

    except Exception as err:
        st.error(f"🚨 Gagal Update: {err}")

# --- 8. FOOTER ---
st.divider()
st.caption("Developed by Gramaldy & Darwin - Institut Teknologi Del Interns @ PT Telkom Infrastruktur Indonesia")