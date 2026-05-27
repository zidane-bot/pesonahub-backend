from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, text
from pydantic import BaseModel
import json
import hashlib

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ======================================================
# DATABASE: Neon Cloud (PostgreSQL)
# ======================================================
DATABASE_URL = "postgresql://neondb_owner:npg_7nygpkNP4MZY@ep-silent-base-ao0q5ruj.c-2.ap-southeast-1.aws.neon.tech/neondb?sslmode=require"
engine = create_engine(DATABASE_URL, pool_pre_ping=True)

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

# ======================================================
# ROOT
# ======================================================
@app.get("/")
def read_root():
    return {"pesan": "Welcome to PesonaHub API bree! Neon Cloud Edition"}

# ======================================================
# SETUP DB
# ======================================================
@app.get("/api/setup-db")
def setup_database():
    try:
        with engine.begin() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id SERIAL PRIMARY KEY,
                    username VARCHAR(100) UNIQUE NOT NULL,
                    password VARCHAR(255) NOT NULL,
                    nama_umkm VARCHAR(200),
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """))
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS categories (
                    category_id SERIAL PRIMARY KEY,
                    category_name VARCHAR(100) NOT NULL
                )
            """))
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS templates (
                    template_id SERIAL PRIMARY KEY,
                    category_id INT REFERENCES categories(category_id),
                    title VARCHAR(200),
                    preview_image_url TEXT,
                    canvas_data TEXT
                )
            """))
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS user_designs (
                    design_id SERIAL PRIMARY KEY,
                    user_id INT REFERENCES users(user_id),
                    template_id INT,
                    title VARCHAR(200),
                    design_data TEXT,
                    is_published BOOLEAN DEFAULT FALSE,
                    published_at TIMESTAMP,
                    nama_produk VARCHAR(200),
                    harga VARCHAR(100),
                    kontak_wa VARCHAR(50),
                    preview_image_url TEXT,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """))

            # Safe add columns if not exist
            for col, col_type in [
                ("is_published", "BOOLEAN DEFAULT FALSE"),
                ("published_at", "TIMESTAMP"),
                ("nama_produk", "VARCHAR(200)"),
                ("harga", "VARCHAR(100)"),
                ("kontak_wa", "VARCHAR(50)"),
                ("preview_image_url", "TEXT"),
            ]:
                try:
                    conn.execute(text(
                        f"ALTER TABLE user_designs ADD COLUMN IF NOT EXISTS {col} {col_type}"
                    ))
                except Exception:
                    pass

            # Drop foreign key constraint on template_id to allow custom template_id=0 (blank design)
            try:
                conn.execute(text(
                    "ALTER TABLE user_designs DROP CONSTRAINT IF EXISTS user_designs_template_id_fkey"
                ))
            except Exception:
                pass

            # Truncate templates and categories to sync with frontend formats
            conn.execute(text("TRUNCATE TABLE templates, categories CASCADE"))

            # Seed categories
            conn.execute(text("""
                INSERT INTO categories (category_name)
                VALUES 
                ('Instagram Feed'), 
                ('Poster Promo'), 
                ('Katalog Produk'), 
                ('Template Livestream'), 
                ('Banner Marketplace')
            """))

            # Seed templates
            conn.execute(text("""
                INSERT INTO templates (category_id, title, preview_image_url, canvas_data)
                VALUES 
                (1, 'Promo Diskon Kripik Nusantara',
                 'https://images.unsplash.com/photo-1599487488170-d11ec9c172f0?q=80&w=400',
                 '{"warna_bg": "#F59E0B", "teks_utama": "Potongan 50%", "sub_teks": "Keripik singkong renyah tanpa bahan pengawet.", "brand_teks": "KRIPIK NUSANTARA"}'),
                (2, 'Poster Menu Ayam Bakar',
                 'https://asset.kompas.com/crops/N8WTCiVClutwEkjIgCykYbt1e2Q=/142x72:863x553/1200x800/data/photo/2022/09/27/633297e88244b.jpg',
                 '{"warna_bg": "#0B1B3D", "teks_utama": "Diskon Ayam Bakar", "sub_teks": "Ayam bakar rempah madu lezat meresap sampai ke tulang.", "brand_teks": "AYAM BAKAR PREMAN"}'),
                (4, 'Livestream Overlay Fashion',
                 'https://images.unsplash.com/photo-1483985988355-763728e1935b?q=80&w=400',
                 '{"warna_bg": "#FFFFFF", "teks_utama": "Flash Sale", "sub_teks": "Model terbaru baju lebaran kekinian diskon akhir pekan.", "brand_teks": "FASHION HUB"}'),
                (3, 'Katalog Hijab Syari Modern',
                 'https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?q=80&w=400',
                 '{"warna_bg": "#F8FAFC", "teks_utama": "Hijab Syari Premium", "sub_teks": "Bahan adem premium, jahitan rapi, tersedia banyak warna.", "brand_teks": "HIJAB SYARI"}'),
                (5, 'Banner Toko Shopee Fashion',
                 'https://images.unsplash.com/photo-1441986300917-64674bd600d8?q=80&w=400',
                 '{"warna_bg": "#0B1B3D", "teks_utama": "Fashion Diskon 70%", "sub_teks": "Koleksi busana muslim modern paling trendi masa kini.", "brand_teks": "TOKO UTAMA"}')
            """))

        return {"status": "success", "pesan": "Semua tabel berhasil dibuat/diverifikasi di Neon Cloud!"}
    except Exception as e:
        return {"status": "error", "pesan": str(e)}

# ======================================================
# CHECK DB
# ======================================================
@app.get("/cek-db")
def cek_koneksi_db():
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT category_name FROM categories"))
            kategori = [row[0] for row in result]
            return {"status": "Sukses Konek ke Neon Cloud!", "data_kategori": kategori}
    except Exception as e:
        return {"status": "Gagal Konek", "error": str(e)}

# ======================================================
# AUTH
# ======================================================
class RegisterInput(BaseModel):
    username: str
    password: str
    nama_umkm: str

class LoginInput(BaseModel):
    username: str
    password: str

@app.post("/api/auth/register")
def register(data: RegisterInput):
    try:
        with engine.connect() as conn:
            existing = conn.execute(
                text("SELECT user_id FROM users WHERE username = :u"),
                {"u": data.username}
            ).fetchone()
            if existing:
                raise HTTPException(status_code=400, detail="Username sudah dipakai, coba yang lain!")

        with engine.begin() as conn:
            result = conn.execute(
                text("""
                    INSERT INTO users (username, password, nama_umkm)
                    VALUES (:username, :password, :nama_umkm)
                    RETURNING user_id, username, nama_umkm
                """),
                {
                    "username": data.username,
                    "password": hash_password(data.password),
                    "nama_umkm": data.nama_umkm,
                }
            )
            row = result.fetchone()
            return {
                "status": "success",
                "pesan": f"Selamat datang {data.nama_umkm}! Akun berhasil dibuat.",
                "user": {"user_id": row[0], "username": row[1], "nama_umkm": row[2]}
            }
    except HTTPException:
        raise
    except Exception as e:
        return {"status": "error", "pesan": str(e)}

@app.post("/api/auth/login")
def login(data: LoginInput):
    try:
        with engine.connect() as conn:
            row = conn.execute(
                text("SELECT user_id, username, nama_umkm, password FROM users WHERE username = :u"),
                {"u": data.username}
            ).fetchone()

        if not row:
            raise HTTPException(status_code=401, detail="Username tidak ditemukan!")
        if row[3] != hash_password(data.password):
            raise HTTPException(status_code=401, detail="Password salah!")

        return {
            "status": "success",
            "pesan": f"Selamat datang kembali, {row[2]}!",
            "user": {"user_id": row[0], "username": row[1], "nama_umkm": row[2]}
        }
    except HTTPException:
        raise
    except Exception as e:
        return {"status": "error", "pesan": str(e)}

# ======================================================
# TEMPLATES
# ======================================================
@app.get("/api/templates")
def get_semua_template():
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT t.template_id, t.title, c.category_name, t.preview_image_url, t.canvas_data 
                FROM templates t
                JOIN categories c ON t.category_id = c.category_id
            """))
            data = [
                {"id": r[0], "judul": r[1], "kategori": r[2], "gambar": r[3], "canvas_data": r[4]}
                for r in result
            ]
        return {"status": "success", "data": data}
    except Exception as e:
        return {"status": "error", "pesan": str(e)}

class SaveTemplateRequest(BaseModel):
    canvas_data: dict
    title: str | None = None
    preview_image_url: str | None = None

@app.post("/api/templates")
def create_template(req: SaveTemplateRequest):
    try:
        with engine.connect() as conn:
            cat = conn.execute(text("SELECT category_id FROM categories LIMIT 1")).fetchone()
            cat_id = cat[0] if cat else 1

        with engine.begin() as conn:
            result = conn.execute(
                text("""
                    INSERT INTO templates (category_id, title, preview_image_url, canvas_data)
                    VALUES (:cat_id, :title, :preview, :canvas)
                    RETURNING template_id
                """),
                {
                    "cat_id": cat_id,
                    "title": req.title or "Promo Baru",
                    "preview": req.preview_image_url or "",
                    "canvas": json.dumps(req.canvas_data),
                }
            )
            new_id = result.fetchone()[0]
        return {"status": "success", "pesan": "Template baru berhasil dibuat!", "id": new_id}
    except Exception as e:
        return {"status": "error", "pesan": str(e)}

@app.post("/api/templates/{template_id}")
def update_template(template_id: int, req: SaveTemplateRequest):
    try:
        with engine.begin() as conn:
            conn.execute(
                text("UPDATE templates SET canvas_data = :canvas WHERE template_id = :tid"),
                {"canvas": json.dumps(req.canvas_data), "tid": template_id}
            )
            if req.title:
                conn.execute(
                    text("UPDATE templates SET title = :title WHERE template_id = :tid"),
                    {"title": req.title, "tid": template_id}
                )
            if req.preview_image_url:
                conn.execute(
                    text("UPDATE templates SET preview_image_url = :preview WHERE template_id = :tid"),
                    {"preview": req.preview_image_url, "tid": template_id}
                )
        return {"status": "success", "pesan": "Template berhasil disimpan!", "id": template_id}
    except Exception as e:
        return {"status": "error", "pesan": str(e)}

# ======================================================
# USER DESIGNS
# ======================================================
class DesignInput(BaseModel):
    user_id: int
    template_id: int
    title: str
    design_data: dict
    nama_produk: str | None = None
    harga: str | None = None
    kontak_wa: str | None = None
    preview_image_url: str | None = None

@app.post("/api/designs")
def simpan_desain(desain: DesignInput):
    try:
        with engine.begin() as conn:
            result = conn.execute(
                text("""
                    INSERT INTO user_designs 
                    (user_id, template_id, title, design_data, nama_produk, harga, kontak_wa, preview_image_url)
                    VALUES (:uid, :tid, :title, :data, :nama, :harga, :wa, :preview)
                    RETURNING design_id
                """),
                {
                    "uid": desain.user_id,
                    "tid": desain.template_id,
                    "title": desain.title,
                    "data": json.dumps(desain.design_data),
                    "nama": desain.nama_produk,
                    "harga": desain.harga,
                    "wa": desain.kontak_wa,
                    "preview": desain.preview_image_url,
                }
            )
            new_id = result.fetchone()[0]
        return {"status": "success", "pesan": "Desain berhasil disimpan!", "design_id": new_id}
    except Exception as e:
        return {"status": "error", "pesan": str(e)}

class PublishInput(BaseModel):
    nama_produk: str
    harga: str
    kontak_wa: str

@app.post("/api/designs/{design_id}/publish")
def publish_desain(design_id: int, data: PublishInput):
    try:
        with engine.begin() as conn:
            conn.execute(
                text("""
                    UPDATE user_designs
                    SET is_published = TRUE,
                        published_at = NOW(),
                        nama_produk = :nama,
                        harga = :harga,
                        kontak_wa = :wa
                    WHERE design_id = :did
                """),
                {"did": design_id, "nama": data.nama_produk, "harga": data.harga, "wa": data.kontak_wa}
            )
        return {"status": "success", "pesan": "Desain berhasil dipublish ke etalase!"}
    except Exception as e:
        return {"status": "error", "pesan": str(e)}

# ======================================================
# ETALASE PUBLIK
# ======================================================
@app.get("/api/etalase")
def get_etalase():
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT 
                    ud.design_id, ud.title, ud.nama_produk, ud.harga, ud.kontak_wa,
                    ud.preview_image_url, ud.published_at, u.nama_umkm, u.username
                FROM user_designs ud
                JOIN users u ON ud.user_id = u.user_id
                WHERE ud.is_published = TRUE
                ORDER BY ud.published_at DESC
                LIMIT 50
            """))
            items = [
                {
                    "design_id": r[0], "title": r[1], "nama_produk": r[2],
                    "harga": r[3], "kontak_wa": r[4], "preview_image_url": r[5],
                    "published_at": str(r[6]) if r[6] else None,
                    "nama_umkm": r[7], "username": r[8],
                }
                for r in result
            ]
        return {"status": "success", "data": items}
    except Exception as e:
        return {"status": "error", "pesan": str(e)}

@app.get("/api/my-designs/{user_id}")
def get_my_designs(user_id: int):
    try:
        with engine.connect() as conn:
            result = conn.execute(
                text("""
                    SELECT design_id, title, nama_produk, harga, preview_image_url, is_published, created_at
                    FROM user_designs
                    WHERE user_id = :uid
                    ORDER BY created_at DESC
                """),
                {"uid": user_id}
            )
            items = [
                {
                    "design_id": r[0], "title": r[1], "nama_produk": r[2],
                    "harga": r[3], "preview_image_url": r[4],
                    "is_published": r[5], "created_at": str(r[6]) if r[6] else None,
                }
                for r in result
            ]
        return {"status": "success", "data": items}
    except Exception as e:
        return {"status": "error", "pesan": str(e)}