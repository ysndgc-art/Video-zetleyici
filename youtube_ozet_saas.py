import streamlit as st
import json
import os
import re
import urllib.request
import urllib.parse
from datetime import datetime
import yt_dlp
from openai import OpenAI

# --- SAYFA YAPILANDIRMASI ---
st.set_page_config(page_title="AI Video & Metin Analiz SaaS", page_icon="📺", layout="wide")

VERITABANI_DOSYASI = "ozet_gecmisi.json"

def veritabani_yukle():
    try:
        if os.path.exists(VERITABANI_DOSYASI):
            f = open(VERITABANI_DOSYASI, "r", encoding="utf-8")
            veri = json.load(f)
            f.close()
            if isinstance(veri, list):
                return {"gecmis": veri}
            if isinstance(veri, dict) and "gecmis" in veri:
                if isinstance(veri["gecmis"], list):
                    return veri
    except:
        pass
    return {"gecmis": []}

def veritabani_kaydet(veri):
    try:
        f = open(VERITABANI_DOSYASI, "w", encoding="utf-8")
        json.dump(veri, f, ensure_ascii=False, indent=4)
        f.close()
    except:
        pass

def gecmis_ekle(yeni_ozet):
    veri = veritabani_yukle()
    if not isinstance(veri, dict) or "gecmis" not in veri:
        veri = {"gecmis": []}
    if not any(g.get('metin', '')[:30] == yeni_ozet['metin'][:30] for g in veri["gecmis"]):
        veri["gecmis"].insert(0, yeni_ozet)
        veritabani_kaydet(veri)

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

def yerel_mantik_ozetleyici(metin, madde_sayisi=5, dil="tr"):
    temiz_metin = re.sub(r'\[.*?\]', '', metin)
    temiz_metin = re.sub(r'\(.*?\)', '', temiz_metin)
    temiz_metin = re.sub(r'\s+', ' ', temiz_metin).strip()
    
    if "." not in temiz_metin or temiz_metin.count(".") < 3:
        ham_kelimeler = temiz_metin.split()
        parçalanmış_cumleler = []
        for i in range(0, len(ham_kelimeler), 15):
            grup = ham_kelimeler[i:i+15]
            parçalanmış_cumleler.append(" ".join(grup) + ".")
        cumleler = parçalanmış_cumleler
    else:
        cumleler = [c.strip() for c in re.split(r'(?<=[.!?])\s+', temiz_metin) if c.strip()]

    if len(cumleler) <= madde_sayisi:
        return [c for c in cumleler if len(c.split()) > 3]

    kelimeler = re.findall(r'\w+', temiz_metin.lower())
    if dil == "tr":
        durma_kelimeleri = {"ve", "veya", "ama", "fakat", "ile", "bir", "bu", "için", "gibi", "da", "de"}
    else:
        durma_kelimeleri = {"the", "and", "you", "that", "was", "for", "on", "are", "with", "this"}
    
    frekanslar = {}
    for k in kelimeler:
        if k not in durma_kelimeleri and len(k) > 3:
            frekanslar[k] = frekanslar.get(k, 0) + 1

    cumle_puanlari = {}
    for idx, cumle in enumerate(cumleler):
        puan = 0
        kelime_listesi = re.findall(r'\w+', cumle.lower())
        if len(kelime_listesi) < 4 or len(kelime_listesi) > 30:
            continue
        for kelime in kelime_listesi:
            if kelime in frekanslar:
                puan += frekanslar[kelime]
        cumle_puanlari[idx] = puan

    if not cumle_puanlari:
        return [c for c in cumleler[:madde_sayisi]]

    en_iyi_indeksler = sorted(cumle_puanlari, key=cumle_puanlari.get, reverse=True)[:madde_sayisi]
    en_iyi_indeksler.sort()

    sonuc = []
    for idx in en_iyi_indeksler:
        ham_cumle = cumleler[idx].strip()
        if ham_cumle:
            yarisi = len(ham_cumle) // 2
            sol = ham_cumle[:yarisi].strip().lower()
            sag = ham_cumle[yarisi:].strip().lower()
            if sol[:10] == sag[:10]:
                ham_cumle = ham_cumle[:yarisi].strip()
            
            ham_cumle = ham_cumle.strip()
            if ham_cumle:
                ham_cumle = ham_cumle.upper() + ham_cumle[1:]
                if not ham_cumle.endswith("."):
                    ham_cumle += "."
                sonuc.append(ham_cumle)
    return sonuc

def whisper_ile_ses_analizi(video_id, api_anahtari):
    if not api_anahtari:
        st.error("❌ OpenAI API Key girmeden video analizi yapılamaz. Lütfen sol menüden anahtarınızı girin.")
        return None
    
    hedef_dosya = f"audio_{video_id}.m4a"
    
    # yt-dlp için Streamlit Cloud'u yormayacak ultra hafif ayarlar
    ydl_opts = {
        'format': 'm4a/bestaudio/best',
        'outtmpl': f"audio_{video_id}.%(ext)s",
        'quiet': True,
        'no_warnings': True,
        'noprogress': True,
        'socket_timeout': 30,
        'retries': 3,
        'extractor_args': {'youtube': {'clients': ['tv', 'android']}} # IP Engelini Aşmak İçin Mobil/TV Taklidi
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([f"https://youtube.com{video_id}"])
            
        if os.path.exists(hedef_dosya):
            client = OpenAI(api_key=api_anahtari)
            with open(hedef_dosya, "rb") as f:
                transcription = client.audio.transcriptions.create(
                    model="whisper-1", 
                    file=f
                )
            # Geçici dosyayı temizle
            try: os.remove(hedef_dosya)
            except: pass
            return transcription.text
    except Exception as e:
        st.error(f"🚨 Ses Çözme Hatası: {str(e)}")
        if os.path.exists(hedef_dosya):
            try: os.remove(hedef_dosya)
            except: pass
    return None

def rapor_formatlarini_uret(tarih, saat, maddeler, baslik_url=""):
    txt_cikisi = f"--- AI ANALIZ RAPORU ---\nTarih: {tarih} - {saat}\n"
    if baslik_url: txt_cikisi += f"Kaynak: {baslik_url}\n"
    txt_cikisi += "\nKritik Maddeler:\n"
    for m in maddeler: txt_cikisi += f"{m}\n"
    return txt_cikisi

# --- SIDEBAR ---
st.sidebar.title("📜 Analiz Geçmişiniz")
veri_havuzu = veritabani_yukle()
gecmis_listesi = veri_havuzu.get("gecmis", [])
if isinstance(gecmis_listesi, list) and gecmis_listesi:
    for sira, g in enumerate(gecmis_listesi[:10]):
        if st.sidebar.button(f"⏱️ {g.get('saat','')} - {g.get('metin','')[:15]}...", key=f"hist_{sira}"):
            st.session_state["aktif_ozet"] = g
else:
    st.sidebar.info("Henüz geçmiş analiz bulunmuyor.")

st.sidebar.divider()
st.sidebar.title("🔑 API Ayarları")
env_key = os.getenv("OPENAI_API_KEY", "")
openai_key = st.sidebar.text_input("OpenAI API Key:", value=env_key, type="password", placeholder="sk-proj-...")

# --- ANA SAYFA PANELİ ---
st.title("📺 AI Akıllı Video & Metin Yorumlayıcı SaaS")
st.write("Gelişmiş İstatistik Paneli ve Kolay Dışa Aktarma Sistemi")
st.divider()

madde_limiti = st.slider("Çıkarılacak Kritik Madde Sayısı:", min_value=3, max_value=15, value=5, step=1)

# MODLAR
st.subheader("📺 1. Mod: YouTube Video Analizi")
video_linki = st.text_input("YouTube Linki veya Kodu:", value="", placeholder="https://youtube.com...", key="main_yt_box")
if st.button("🚀 Videoyu İndir ve Yapay Zekayla Yorumla", key="main_yt_btn"):
    if not video_linki.strip():
        st.warning("Lütfen bir YouTube linki girin.")
    else:
        v_id = youtube_id_bul_kesin(video_linki)
        st.info("📥 Sunucu IP engeli Whisper motoruyla aşılıyor. Ses akışı analiz ediliyor (Bu işlem videonun uzunluğuna göre biraz sürebilir)...")
        metin = whisper_ile_ses_analizi(v_id, openai_key)
        if not metin:
            st.error("❌ Ses dosyası çözülemedi. Lütfen API anahtarınızı kontrol edin veya videonun herkese açık olduğundan emin olun.")
        else:
            st.success("🎉 Ses başarıyla metne dönüştürüldü! Maddeler çıkarılıyor...")
            ham_maddeler = yerel_mantik_ozetleyici(metin, madde_sayisi=madde_limiti, dil="tr")
            ozet_maddeleri = [f"📌 {m}" for m in ham_maddeler]
            simdi = datetime.now()
            veri_paketi = {"tarih": simdi.strftime("%d.%m.%Y"), "saat": simdi.strftime("%H:%M:%S"), "metin": metin, "ozet": ozet_maddeleri}
            gecmis_ekle(veri_paketi)
            st.session_state["aktif_ozet"] = veri_paketi
            st.rerun()

st.divider()

st.subheader("📝 2. Mod: Doğrudan Metin Analizi")
girilen_metin = st.text_area("Yorumlanacak Uzun Metni Yapıştırın:", height=150, key="main_text_box")
if st.button("⚡ Metni Analiz Et", key="main_text_btn"):
    if not girilen_metin.strip():
        st.warning("Lütfen metin girin.")
    else:
        ham_maddeler = yerel_mantik_ozetleyici(girilen_metin, madde_sayisi=madde_limiti, dil="tr")
        ozet_maddeleri = [f"💡 {m}" for m in ham_maddeler]
        simdi = datetime.now()
        veri_paketi = {"tarih": simdi.strftime("%d.%m.%Y"), "saat": simdi.strftime("%H:%M:%S"), "metin": girilen_metin, "ozet": ozet_maddeleri}
        gecmis_ekle(veri_paketi)
        st.session_state["aktif_ozet"] = veri_paketi
        st.rerun()

# --- SONUÇ ALANI ---
if "aktif_ozet" in st.session_state and st.session_state["aktif_ozet"] is not None:
    st.divider()
    st.info("📂 **Analiz Sonucu**")
    g = st.session_state["aktif_ozet"]
    if isinstance(g, dict) and "ozet" in g:
        for m in g.get('ozet', []):
            st.write(m)
        st.divider()
        t_fmt = rapor_formatlarini_uret(g.get('tarih',''), g.get('saat',''), g.get('ozet', []))
        st.download_button(label="📥 TXT Olarak İndir", data=t_fmt.encode('utf-8'), file_name="analiz.txt", mime="text/plain", key="down_btn")
