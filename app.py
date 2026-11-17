"""
Kas Sekolah - Aplikasi Pengelolaan Kas Kelas
Python + Streamlit + SQLite
Jalankan: streamlit run app.py
"""

import streamlit as st
import sqlite3
import hashlib
from datetime import date, datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "kas_sekolah.db"

# ==================== DATABASE ====================
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_conn()
    c = conn.cursor()
    c.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            nama_lengkap TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('admin','bendahara','siswa'))
        );
        CREATE TABLE IF NOT EXISTS pengaturan (
            jenis TEXT PRIMARY KEY,
            jumlah REAL NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS uang_masuk (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            siswa_id INTEGER NOT NULL,
            jumlah REAL NOT NULL,
            jenis TEXT NOT NULL,
            tanggal TEXT NOT NULL,
            dicatat_oleh INTEGER,
            FOREIGN KEY (siswa_id) REFERENCES users(id)
        );
        CREATE TABLE IF NOT EXISTS uang_keluar (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            jumlah REAL NOT NULL,
            keperluan TEXT NOT NULL,
            tanggal TEXT NOT NULL,
            dicatat_oleh INTEGER
        );
    """)
    # Seed admin & pengaturan
    c.execute("SELECT COUNT(*) FROM users WHERE username='admin'")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO users (username,password,nama_lengkap,role) VALUES (?,?,?,?)",
                  ("admin", hash_pw("admin123"), "Administrator", "admin"))
        c.execute("INSERT INTO users (username,password,nama_lengkap,role) VALUES (?,?,?,?)",
                  ("bendahara", hash_pw("bendahara123"), "Bendahara Kelas", "bendahara"))
        c.execute("INSERT INTO users (username,password,nama_lengkap,role) VALUES (?,?,?,?)",
                  ("siswa1", hash_pw("siswa123"), "Ahmad Siswa", "siswa"))
    for jenis, jml in [("harian", 5000), ("mingguan", 25000), ("bulanan", 100000)]:
        c.execute("INSERT OR IGNORE INTO pengaturan (jenis, jumlah) VALUES (?,?)", (jenis, jml))
    conn.commit()
    conn.close()

def hash_pw(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

def format_rp(n):
    return f"Rp {n:,.0f}".replace(",", ".")

# ==================== AUTH ====================
def login(username, password):
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM users WHERE username=? AND password=?",
        (username.strip().lower(), hash_pw(password))
    ).fetchone()
    conn.close()
    return dict(row) if row else None

def register(username, password, nama, role):
    conn = get_conn()
    try:
        conn.execute(
            "INSERT INTO users (username,password,nama_lengkap,role) VALUES (?,?,?,?)",
            (username.strip().lower(), hash_pw(password), nama.strip(), role)
        )
        conn.commit()
        conn.close()
        return True, "Akun berhasil dibuat!"
    except sqlite3.IntegrityError:
        conn.close()
        return False, "Username sudah dipakai."

# ==================== PAGE CONFIG ====================
st.set_page_config(page_title="Kas Sekolah", page_icon="💰", layout="wide")
init_db()

# Session state
if "user" not in st.session_state:
    st.session_state.user = None

# ==================== LOGIN / REGISTER ====================
if st.session_state.user is None:
    st.markdown("## 💰 Kas Sekolah")
    st.caption("Sistem Pengelolaan Kas Kelas")

    tab1, tab2 = st.tabs(["Masuk", "Daftar Akun"])

    with tab1:
        with st.form("login_form"):
            u = st.text_input("Username")
            p = st.text_input("Password", type="password")
            if st.form_submit_button("Masuk", use_container_width=True):
                user = login(u, p)
                if user:
                    st.session_state.user = user
                    st.rerun()
                else:
                    st.error("Username atau password salah")

        st.info("**Akun Demo**\n- Admin: `admin` / `admin123`\n- Bendahara: `bendahara` / `bendahara123`\n- Siswa: `siswa1` / `siswa123`")

    with tab2:
        with st.form("reg_form"):
            nama = st.text_input("Nama Lengkap")
            un = st.text_input("Username (min 3 karakter)")
            pw = st.text_input("Password (min 4 karakter)", type="password")
            role = st.selectbox("Daftar Sebagai", ["siswa", "bendahara"])
            if st.form_submit_button("Buat Akun", use_container_width=True):
                if len(un) < 3 or len(pw) < 4 or not nama:
                    st.error("Lengkapi data dengan benar")
                else:
                    ok, msg = register(un, pw, nama, role)
                    if ok:
                        st.success(msg)
                    else:
                        st.error(msg)
    st.stop()

# ==================== LOGGED IN ====================
user = st.session_state.user
role = user["role"]

# Sidebar
with st.sidebar:
    st.markdown(f"### 💰 Kas Sekolah")
    st.write(f"**{user['nama_lengkap']}**")
    st.caption(role.upper())
    st.divider()

    if role == "admin":
        menu = st.radio("Menu", ["Dashboard", "Kelola User", "Pengaturan Kas", "Status Bayar", "Laporan"], label_visibility="collapsed")
    elif role == "bendahara":
        menu = st.radio("Menu", ["Dashboard", "Uang Masuk", "Uang Keluar", "Laporan"], label_visibility="collapsed")
    else:
        menu = st.radio("Menu", ["Dashboard", "Laporan"], label_visibility="collapsed")

    st.divider()
    if st.button("Keluar", use_container_width=True):
        st.session_state.user = None
        st.rerun()

# ==================== HELPERS ====================
def get_totals():
    conn = get_conn()
    masuk = conn.execute("SELECT COALESCE(SUM(jumlah),0) FROM uang_masuk").fetchone()[0]
    keluar = conn.execute("SELECT COALESCE(SUM(jumlah),0) FROM uang_keluar").fetchone()[0]
    conn.close()
    return masuk, keluar

def get_siswa():
    conn = get_conn()
    rows = conn.execute("SELECT id, username, nama_lengkap FROM users WHERE role='siswa' ORDER BY nama_lengkap").fetchall()
    conn.close()
    return rows

# ==================== DASHBOARD ====================
if menu == "Dashboard":
    st.title("Dashboard")
    masuk, keluar = get_totals()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Pemasukan", format_rp(masuk))
    c2.metric("Pengeluaran", format_rp(keluar))
    c3.metric("Saldo", format_rp(masuk - keluar))
    if role == "admin":
        c4.metric("Jumlah Siswa", len(get_siswa()))
    elif role == "siswa":
        conn = get_conn()
        saya = conn.execute("SELECT COALESCE(SUM(jumlah),0) FROM uang_masuk WHERE siswa_id=?", (user["id"],)).fetchone()[0]
        conn.close()
        c4.metric("Bayar Saya", format_rp(saya))
    else:
        c4.metric("Role", "Bendahara")

    st.info(f"Halo **{user['nama_lengkap']}**! Gunakan menu di kiri untuk navigasi.")

# ==================== KELOLA USER (Admin) ====================
elif menu == "Kelola User" and role == "admin":
    st.title("Kelola User")
    st.subheader("Tambah Bendahara / Siswa")
    with st.form("add_user"):
        col1, col2 = st.columns(2)
        with col1:
            nama = st.text_input("Nama Lengkap")
            username = st.text_input("Username")
        with col2:
            password = st.text_input("Password", value="siswa123")
            role_new = st.selectbox("Role", ["siswa", "bendahara"])
        if st.form_submit_button("Tambah User"):
            ok, msg = register(username, password, nama, role_new)
            if ok:
                st.success(msg)
                st.rerun()
            else:
                st.error(msg)

    st.subheader("Daftar User")
    conn = get_conn()
    users = conn.execute("SELECT id, username, nama_lengkap, role FROM users WHERE role != 'admin' ORDER BY role, nama_lengkap").fetchall()
    conn.close()
    for u in users:
        col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
        col1.write(u["nama_lengkap"])
        col2.write(u["username"])
        col3.write(u["role"])
        if col4.button("Hapus", key=f"del_{u['id']}"):
            conn = get_conn()
            conn.execute("DELETE FROM users WHERE id=?", (u["id"],))
            conn.commit()
            conn.close()
            st.rerun()

# ==================== PENGATURAN KAS (Admin) ====================
elif menu == "Pengaturan Kas" and role == "admin":
    st.title("Pengaturan Kas")
    st.caption("Tentukan besaran iuran per siswa")
    conn = get_conn()
    settings = {r["jenis"]: r["jumlah"] for r in conn.execute("SELECT * FROM pengaturan").fetchall()}
    conn.close()

    with st.form("settings"):
        harian = st.number_input("Kas Harian (Rp)", value=float(settings.get("harian", 5000)), min_value=0.0, step=500.0)
        mingguan = st.number_input("Kas Mingguan (Rp)", value=float(settings.get("mingguan", 25000)), min_value=0.0, step=1000.0)
        bulanan = st.number_input("Kas Bulanan (Rp)", value=float(settings.get("bulanan", 100000)), min_value=0.0, step=5000.0)
        if st.form_submit_button("Simpan"):
            conn = get_conn()
            for j, v in [("harian", harian), ("mingguan", mingguan), ("bulanan", bulanan)]:
                conn.execute("UPDATE pengaturan SET jumlah=? WHERE jenis=?", (v, j))
            conn.commit()
            conn.close()
            st.success("Pengaturan disimpan!")
            st.rerun()

# ==================== STATUS BAYAR (Admin) ====================
elif menu == "Status Bayar" and role == "admin":
    st.title("Status Pembayaran Siswa")
    jenis = st.selectbox("Jenis Periode", ["harian", "mingguan", "bulanan"])
    conn = get_conn()
    target = conn.execute("SELECT jumlah FROM pengaturan WHERE jenis=?", (jenis,)).fetchone()["jumlah"]
    siswa = get_siswa()
    st.caption(f"Target: {format_rp(target)} / siswa")

    data = []
    for s in siswa:
        bayar = conn.execute(
            "SELECT COALESCE(SUM(jumlah),0) FROM uang_masuk WHERE siswa_id=? AND jenis=?",
            (s["id"], jenis)
        ).fetchone()[0]
        data.append({
            "Nama": s["nama_lengkap"],
            "Username": s["username"],
            "Status": "✅ Lunas" if bayar >= target else "❌ Belum",
            "Dibayar": format_rp(bayar)
        })
    conn.close()
    st.dataframe(data, use_container_width=True, hide_index=True)

# ==================== UANG MASUK (Bendahara) ====================
elif menu == "Uang Masuk" and role in ("bendahara", "admin"):
    st.title("Catat Uang Masuk")
    jenis = st.selectbox("Jenis Kas", ["harian", "mingguan", "bulanan"])
    conn = get_conn()
    jumlah = conn.execute("SELECT jumlah FROM pengaturan WHERE jenis=?", (jenis,)).fetchone()["jumlah"]
    st.info(f"Nominal: **{format_rp(jumlah)}** per siswa")

    siswa = get_siswa()
    # Yang belum bayar
    belum = []
    for s in siswa:
        cek = conn.execute(
            "SELECT id FROM uang_masuk WHERE siswa_id=? AND jenis=? LIMIT 1",
            (s["id"], jenis)
        ).fetchone()
        if not cek:
            belum.append(s)

    if not belum:
        st.success("Semua siswa sudah tercatat untuk periode ini.")
    else:
        options = {f"{s['nama_lengkap']} ({s['username']})": s["id"] for s in belum}
        dipilih = st.multiselect("Pilih siswa yang sudah bayar", list(options.keys()))
        if st.button("Simpan Pembayaran", type="primary"):
            for nama in dipilih:
                sid = options[nama]
                conn.execute(
                    "INSERT INTO uang_masuk (siswa_id, jumlah, jenis, tanggal, dicatat_oleh) VALUES (?,?,?,?,?)",
                    (sid, jumlah, jenis, str(date.today()), user["id"])
                )
            conn.commit()
            st.success(f"{len(dipilih)} siswa berhasil dicatat!")
            st.rerun()
    conn.close()

# ==================== UANG KELUAR (Bendahara) ====================
elif menu == "Uang Keluar" and role in ("bendahara", "admin"):
    st.title("Catat Uang Keluar")
    with st.form("keluar_form"):
        col1, col2 = st.columns(2)
        with col1:
            jumlah = st.number_input("Jumlah (Rp)", min_value=1.0, step=1000.0)
        with col2:
            tanggal = st.date_input("Tanggal", value=date.today())
        keperluan = st.text_input("Keperluan / Dipakai Untuk", placeholder="Contoh: Beli ATK, konsumsi rapat")
        if st.form_submit_button("Simpan Pengeluaran"):
            if not keperluan:
                st.error("Isi keperluan")
            else:
                conn = get_conn()
                conn.execute(
                    "INSERT INTO uang_keluar (jumlah, keperluan, tanggal, dicatat_oleh) VALUES (?,?,?,?)",
                    (jumlah, keperluan, str(tanggal), user["id"])
                )
                conn.commit()
                conn.close()
                st.success("Pengeluaran disimpan!")
                st.rerun()

    st.subheader("Rekap Pengeluaran")
    filter_k = st.radio("Filter", ["Semua", "Hari Ini", "Bulan Ini"], horizontal=True)
    conn = get_conn()
    if filter_k == "Hari Ini":
        rows = conn.execute("SELECT * FROM uang_keluar WHERE tanggal=? ORDER BY id DESC", (str(date.today()),)).fetchall()
    elif filter_k == "Bulan Ini":
        bulan = date.today().strftime("%Y-%m")
        rows = conn.execute("SELECT * FROM uang_keluar WHERE tanggal LIKE ? ORDER BY id DESC", (bulan + "%",)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM uang_keluar ORDER BY id DESC").fetchall()
    conn.close()

    if rows:
        st.dataframe([{
            "Tanggal": r["tanggal"],
            "Keperluan": r["keperluan"],
            "Jumlah": format_rp(r["jumlah"])
        } for r in rows], use_container_width=True, hide_index=True)
    else:
        st.caption("Belum ada data pengeluaran.")

# ==================== LAPORAN ====================
elif menu == "Laporan":
    st.title("Laporan Kas")
    masuk, keluar = get_totals()
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Masuk", format_rp(masuk))
    c2.metric("Total Keluar", format_rp(keluar))
    c3.metric("Saldo", format_rp(masuk - keluar))

    conn = get_conn()
    st.subheader("Uang Masuk")
    rows_m = conn.execute("""
        SELECT um.tanggal, um.jenis, um.jumlah, u.nama_lengkap
        FROM uang_masuk um JOIN users u ON um.siswa_id = u.id
        ORDER BY um.id DESC LIMIT 50
    """).fetchall()
    if rows_m:
        st.dataframe([{
            "Tanggal": r["tanggal"],
            "Siswa": r["nama_lengkap"],
            "Jenis": r["jenis"],
            "Jumlah": format_rp(r["jumlah"])
        } for r in rows_m], use_container_width=True, hide_index=True)
    else:
        st.caption("Belum ada data.")

    st.subheader("Uang Keluar")
    rows_k = conn.execute("SELECT * FROM uang_keluar ORDER BY id DESC LIMIT 50").fetchall()
    if rows_k:
        st.dataframe([{
            "Tanggal": r["tanggal"],
            "Keperluan": r["keperluan"],
            "Jumlah": format_rp(r["jumlah"])
        } for r in rows_k], use_container_width=True, hide_index=True)
    else:
        st.caption("Belum ada data.")
    conn.close()
