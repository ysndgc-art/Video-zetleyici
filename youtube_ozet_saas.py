import streamlit as st
import json
import os
import re
from datetime import datetime
import yt_dlp

# --- SAYFA YAPILANDIRMASI ---
st.set_page_config(page_title="AI Video & Metin Özetleyici SaaS", page_icon="📺", layout="wide")

VERITABANI_DOSYASI = "ozet_gecmisi.json"

def veritabani_yukle():
    if os.path.exists(VERITABANI_DOSYASI):
        with open(VERITABANI_DOSYASI, "r", encoding="utf-8") as f:
            try: return json.load(f)
            except: return []
    return []

def veritabani_kaydet(yeni_ozet):
    gecmis = veritabani_yukle()
    # Mükerrer kayıt kontrolü
    if not any(g['metin'][:30] == yeni_ozet['metin'][:30] for g in gecmis):
        gecmis.insert(0, yeni_ozet)
        with open(VERITABANI_DOSYASI, "w", encoding="utf-8") as f:
            json.dump(gecmis, f, ensure_ascii=False, indent=4)

def youtube_id_bul_kesin(link):
    girdi = str(link).strip()
    if len(girdi) == 11 and not "/" in girdi and not "." in girdi and not "?" in girdi:
        return girdi
    bulunan = re.findall(r'[a-zA-Z0-9_-]{11}', girdi)
    if bulunan:
        for parca in bulunan:
            if parca.lower() not in ["youtube", "youtu", "watch", "embed"]:
                return parca
    return girdi

# --- 🧠 LOKAL AKILLI ANALİZ MOTORU (SIFIR BAĞLANTI HATASI) ---
def yerel_mantik_ozetleyici(metin):
    # Metni cümlelere ayır
    cumleler = [c.strip() for c in re.split(r'(?<=[.!?])\s+', metin.strip()) if c.strip()]
    if len(cumleler) <= 5:
        return cumleler

    # Kelime frekanslarını hesapla (Etkisiz kelimeleri filtrele)
    kelimeler = re.findall(r'\w+', metin.lower())
    durma_kelimeleri = {
        "ve", "veya", "ama", "fakat", "ile", "bir", "bu", "şu", "o", "da", "de", 
        "için", "gibi", "çok", "en", "daha", "olan", "olarak", "ki", "yani", "böyle"
    }
    
    frekanslar = {}
    for k in kelimeler:
        if k not in durma_kelimeleri and len(k) > 2:
            frekanslar[k] = frekanslar.get(k, 0) + 1

    # Cümleleri içerdikleri önemli kelimelerin ağırlığına göre puanla
    cumle_puanlari = {}
    for idx, cumle in enumerate(cumleler):
        puan = 0
        for kelime in re.findall(r'\w+', cumle.lower()):
            if kelime in frekanslar:
                puan += frekanslar[kelime]
        cumle_puanlari[idx] = puan

    # En yüksek puan alan 5 cümleyi seç ve kronolojik sıraya diz
    en_iyi_indeksler = sorted(cumle_puanlari, key=cumle_puanlari.get, reverse=True)[:5]
    en_iyi_indeksler.sort()

    return [cumleler[idx] for idx in en_iyi_indeksler]

def ytdlp_altyazi_cek(video_id, cerez_yolu):
    safe_id = str(video_id).strip()
    ydl_opts = {
        'writesubtitles': True,
        'writeautomaticsub': True,
        'subtitleslangs': ['tr', 'en', 'auto'],
        'skip_download': True,
        'cookiefile': cerez_yolu,
        'outtmpl': f"sub_{safe_id}",
        'quiet': True,
        'no_warnings': True,
        'ie_key': 'Youtube',
        'force_generic_extractor': False
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([safe_id])
        
        bulunan_dosya = None
        for dosya in os.listdir("."):
            if dosya.startswith(f"sub_{safe_id}") and dosya.endswith(".vtt"):
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
        st.error(f"Altyazı Motor Hatası: {str(e)}")
    return None

# --- SIDEBAR GEÇMİŞ ---
st.sidebar.title("📜 Özet Geçmişiniz")
gecmis = veritabani_yukle()
if gecmis:
    for sira, g in enumerate(gecmis[:10]):
        # Kayıt listesini gösterir
        if st.sidebar.button(f"⏱️ {g.get('saat','')} - {g.get('metin','')[:15]}...", key=f"hist_{sira}"):
            st.session_state["aktif_ozet"] = g
else:
    st.sidebar.info("Henüz geçmiş analiz bulunmuyor.")

if st.sidebar.button("🗑️ Geçmişi Temizle"):
    if os.path.exists(VERITABANI_DOSYASI):
        os.remove(VERITABANI_DOSYASI)
        st.sidebar.success("Geçmiş silindi!")
        st.rerun()

# --- ANA SAYFA ---
st.title("📺 AI Akıllı Video & Metin Özetleyici SaaS")
st.write("Dış Platform Bağımlılığı Olmayan Kararlı Sürüm")
st.divider()

# Geçmişten bir kayıt seçildiyse ekranı güncelle
if "aktif_ozet" in st.session_state:
    st.info("📂 **Geçmiş Özet Görüntüleniyor**")
    g = st.session_state["aktif_ozet"]
    st.success(f"✅ Analiz Tarihi: {g['tarih']} - {g['saat']}")
    st.subheader("📊 Çıkarılan Kritik Maddeler:")
    for madde in g['ozet']:
        st.write(f"🎯 {madde}")
    st.subheader("📝 Orijinal Altyazı Kaynağı:")
    st.caption(g['metin'])
    if st.button("➕ Yeni Özet Ekranına Dön"):
        del st.session_state["aktif_ozet"]
        st.rerun()
else:
    mod = st.radio("Mod Seçin:", ["📺 YouTube Videosu", "📝 Uzun Metin"], horizontal=True)

    if mod == "📺 YouTube Videosu":
        video_linki = st.text_input("YouTube Linki veya Kodu:", value="1OkydHdhABQ")
        if st.button("Videoyu Analiz Et"):
            v_id = youtube_id_bul_kesin(video_linki)
            PROJE_DIZINI = os.path.dirname(os.path.abspath(__file__))
            CEREZ_YOLU = os.path.join(PROJE_DIZINI, "www.youtube.com_cookies.txt")
            
            with st.spinner("📥 1. Adım: Altyazılar YouTube'dan çekiliyor..."):
                metin = ytdlp_altyazi_cek(v_id, CEREZ_YOLU)
                
            if metin:
                with st.spinner("🤖 2. Adım: Cümleler mantıksal süzgeçten geçiriliyor..."):
                    ozet_maddeleri = yerel_mantik_ozetleyici(metin)
                
                simdi = datetime.now()
                tarih_str = simdi.strftime("%d.%m.%Y")
                saat_str = simdi.strftime("%H:%M:%S")
                
                veritabani_kaydet({"tarih": tarih_str, "saat": saat_str, "metin": metin, "ozet": ozet_maddeleri})
                
                st.success("✅ Analiz Tamamlandı!")
                st.subheader("📊 Mantıksal Analiz Sonucu (En Kritik 5 Cümle):")
                for madde in ozet_maddeleri:
                    st.write(f"🎯 {madde}")
                    
                st.subheader("📝 Çekilen Ham Altyazı Metni:")
                st.caption(metin)
            else:
                st.error("Altyazı indirilemedi. Videonun altyazı içerdiğinden emin olun.")

    if mod == "📝 Uzun Metin":
        girilen_metin = st.text_area("Özetlenecek Metni Girin:", height=200)
        if st.button("Metni Özetle"):
            if not girilen_metin.strip():
                st.warning("Metin alanı boş bırakılamaz.")
            else:
                with st.spinner("🤖 Mantıksal süzgeç çalışıyor..."):
                    ozet_maddeleri = yerel_mantik_ozetleyici(girilen_metin)
                
                st.success("✅ İşlem Başarılı!")
                st.subheader("📊 Özet Maddeleri:")
                for madde in ozet_maddeleri:
                    st.write(f"🎯 {madde}")
