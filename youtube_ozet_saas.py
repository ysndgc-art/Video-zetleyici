import streamlit as st
import json
import os
import re
from datetime import datetime
import yt_dlp

# --- SAYFA YAPILANDIRMASI ---
st.set_page_config(page_title="AI Video Özetleyici", page_icon="📺", layout="wide")

VERITABANI_DOSYASI = "ozet_gecmisi.json"

def veritabani_yukle():
    if os.path.exists(VERITABANI_DOSYASI):
        with open(VERITABANI_DOSYASI, "r", encoding="utf-8") as f:
            try: return json.load(f)
            except: return []
    return []

def veritabani_kaydet(yeni_ozet):
    gecmis = veritabani_yukle()
    gecmis.insert(0, yeni_ozet)
    with open(VERITABANI_DOSYASI, "w", encoding="utf-8") as f:
        json.dump(gecmis, f, ensure_ascii=False, indent=4)

def youtube_id_bul_kesin(link):
    girdi = str(link).strip()
    if len(girdi) == 11:
        return girdi
    bulunan = re.findall(r'[a-zA-Z0-9_-]{11}', girdi)
    if bulunan:
        for parca in bulunan:
            if parca.lower() not in ["youtube", "youtu", "watch"]:
                return parca
    return girdi

def akilli_yerel_ozetleyici(metin):
    cumleler = [c.strip() for c in re.split(r'(?<=[.!?])\s+', metin.strip()) if c.strip()]
    if len(cumleler) <= 5:
        return cumleler
    return cumleler[:5]

def ytdlp_altyazi_cek(video_id, cerez_yolu):
    ydl_opts = {
        'writesubtitles': True,
        'writeautomaticsub': True,
        'subtitleslangs': ['tr', 'en', 'auto'],
        'skip_download': True,
        'cookiefile': cerez_yolu,
        'outtmpl': f"sub_{video_id}",
        'quiet': True
    }
    try:
        mutlak_url = f"https://youtube.com{video_id}"
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([mutlak_url])
        
        bulunan_dosya = None
        for dosya in os.listdir("."):
            if dosya.startswith(f"sub_{video_id}") and dosya.endswith(".vtt"):
                bulunan_dosya = dosya
                break
                
        if bulunan_dosya and os.path.exists(bulunan_dosya):
            with open(bulunan_dosya, "r", encoding="utf-8") as f:
                icerik = f.read()
            lines = icerik.split("\n")
            temiz_satirlar = []
            for line in lines:
                if "-->" not in line and line.strip() and not line.strip().isdigit() and "WEBVTT" not in line:
                    clean_line = re.sub(r'<[^>]*>', '', line).strip()
                    if clean_line and (not temiz_satirlar or temiz_satirlar[-1] != clean_line):
                        temiz_satirlar.append(clean_line)
            try: os.remove(bulunan_dosya)
            except: pass
            return " ".join(temiz_satirlar)
    except Exception as e:
        st.error(f"Sistem Hatası: {str(e)}")
    return None

# --- SIDEBAR ---
st.sidebar.title("📜 Özet Geçmişiniz")
gecmis = veritabani_yukle()
for sira, g in enumerate(gecmis[:10]):
    st.sidebar.write(f"⏱️ {g.get('saat','')} - {g.get('metin','')[:15]}...")

# --- ANA SAYFA ---
st.title("📺 AI Akıllı Video & Metin Özetleyici SaaS")
st.write("Kararlı Temiz Sürüm")

mod = st.radio("Mod Seçin:", ["📺 YouTube", "📝 Metin"], horizontal=True)

if mod == "📺 YouTube":
    video_linki = st.text_input("YouTube Linki veya Kodu:", value="1OkydHdhABQ")
    if st.button("Analiz Et"):
        v_id = youtube_id_bul_kesin(video_linki)
        PROJE_DIZINI = os.path.dirname(os.path.abspath(__file__))
        CEREZ_YOLU = os.path.join(PROJE_DIZINI, "www.youtube.com_cookies.txt")
        
        with st.spinner("Altyazılar çekiliyor..."):
            metin = ytdlp_altyazi_cek(v_id, CEREZ_YOLU)
            
        if metin:
            ozet = akilli_yerel_ozetleyici(metin)
            simdi = datetime.now()
            veritabani_kaydet({"tarih": simdi.strftime("%d.%m.%Y"), "saat": simdi.strftime("%H:%M:%S"), "metin": metin, "ozet": ozet})
            st.success("✅ Başarılı!")
            st.subheader("📊 Özet:")
            for m in ozet:
                st.write(f"📌 {m}")
        else:
            st.error("Altyazı bulunamadı.")

if mod == "📝 Metin":
    girilen_metin = st.text_area("Metin girin:")
    if st.button("Özetle"):
        if girilen_metin.strip():
            ozet = akilli_yerel_ozetleyici(girilen_metin)
            st.success("✅ Başarılı!")
            for m in ozet:
                st.write(f"📌 {m}")
