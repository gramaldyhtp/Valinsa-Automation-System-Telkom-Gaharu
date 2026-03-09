import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import re
from datetime import datetime
import time

# --- 1. INITIAL CONFIG (Tampilan Wide sesuai gambar) ---
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

# Ambil ID dan Nama Tabel (Ganti nama worksheet ke FollowUP sesuai gambar)
try:
    S_ID = st.secrets["connections"]["gsheets"]["spreadsheet_id"]
    SHEET_NAME = "FollowUP" # Memastikan nama tabel sesuai gambar Google Sheets Anda
    HAS_CONFIG = True
except Exception:
    HAS_CONFIG = False

# --- 3. UI DESIGN (Header Merah sesuai gambar) ---
st.markdown(
    "<h1 style='text-align: center; color: #EE2D24;'>VALINSA CLOUD SYNC</h1>", 
    unsafe_allow_html=True
)
st.markdown(
    "<p style='text-align: center; color: #555;'>Sistem Otomatisasi Data Infrastruktur - Telkom Infrastruktur Indonesia</p>", 
    unsafe_allow_html=True
)

# Sidebar (Logo Telkom dan Menu sesuai gambar)
with st.sidebar:
    st.image(
        "https://upload.wikimedia.org/wikipedia/commons/thumb/6/6f/Telkom_Indonesia_logo.svg/1200px-Telkom_Indonesia_logo.svg.png", 
        use_container_width=True
    )
    st.subheader("⚙️ Konfigurasi")
    
    if not HAS_CONFIG:
        st.error("⚠️ **Setup Belum Lengkap!**")
        st.info("""
        1. Buat file `.streamlit/secrets.toml` di folder yang sama.
        2. Isi dengan:
        ```toml
        [connections.gsheets]
        spreadsheet_id = "MASUKKAN_ID_SPREADSHEET_DISINI"
        ```
        3. Restart aplikasi.
        """)
        st.stop()
    
    st.divider()
    st.subheader("Profil Penginput")
    user_name = st.text_input(
        "👤 Nama (Gramaldy/Darwin):", 
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
conn_message = ""
conn_data = None

try:
    test_conn = get_connection()
    # Membaca data dengan ttl=0 agar tidak tertahan cache lama
    test_data = test_conn.read(spreadsheet=S_ID, worksheet=SHEET_NAME, ttl=0)
    conn_status = "success"
    conn_message = "✅ Koneksi Google Sheets Berhasil!"
    conn_data = test_data
except Exception as e:
    # Mengembalikan pesan error asli agar mudah didebug (termasuk error Response 200)
    error_msg = str(e)
    conn_status = "error"
    conn_message = f"❌ Koneksi Gagal: {error_msg}"

if conn_status == "success":
    st.success(conn_message)
    if conn_data is not None and not conn_data.empty:
        st.write(f"📊 Total baris di sheet: {len(conn_data)}")
        if "ID Valins" in conn_data.columns:
            st.write(f"✅ Kolom 'ID Valins' terdeteksi.")
        else:
            st.warning("⚠️ Kolom 'ID Valins' tidak ditemukan di Sheet.")
else:
    st.error(conn_message)
    st.info("⚠️ Pastikan Google Sheet sudah di-share ke akun Service Account Anda sebagai EDITOR.")

# --- 5. INPUT AREA ---
st.subheader("📋 Input Data WhatsApp")
raw_input = st.text_area(
    "Paste Data di sini:", 
    height=200, 
    placeholder="Contoh:\nODP-LGB-FA/01 PANEL: 1 VALINS: 12345678",
    key="raw_data"
)

# --- 6. PREVIEW & VALIDASI (Logika Analisis Asli) ---
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

# --- 7. LOGIKA EKSEKUSI (Update Spreadsheet) ---
if preview_df is not None and st.button("🚀 SINRONISASI KE CLOUD", type="primary", use_container_width=True):
    try:
        conn = get_connection()
        with st.spinner("⏳ Mengirim data ke Google Sheets..."):
            df_existing = conn.read(spreadsheet=S_ID, worksheet=SHEET_NAME, ttl=0)
            
            # Gabungkan data lama dan baru (Pastikan worksheet FollowUP ada sesuai gambar)
            if df_existing is not None:
                df_existing = df_existing.dropna(how='all')
                df_final = pd.concat([df_existing, preview_df], ignore_index=True)
            else:
                df_final = preview_df
            
            df_final = df_final.fillna("").astype(str)
            
            # Kirim Update
            conn.update(spreadsheet=S_ID, worksheet=SHEET_NAME, data=df_final)
            
            st.balloons()
            st.success(f"✅ Berhasil! {len(preview_df)} data masuk ke tab {SHEET_NAME}.")
            time.sleep(2)
            st.rerun()

    except Exception as err:
        st.error(f"🚨 Gagal Update: {err}")

# --- 8. FOOTER ---
st.divider()
st.caption("Developed by Gramaldy & Darwin - Institut Teknologi Del Interns @ PT Telkom Infrastruktur Indonesia")