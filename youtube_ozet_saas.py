import streamlit as st
import json
import os
import re
import urllib.request
from datetime import datetime
# Resmi ve en kararlı çalışan YouTube Transkript Kütüphanesi
from youtube_transcript_api import YouTubeTranscriptApi

# --- SAYFA YAPILANDIRMASI ---
st.set_page_config(page_title="AI Video & Metin Analiz SaaS", page_icon="📺", layout="wide")

VERITABANI_DOSYASI = "ozet_gecmisi.json"

def veritabani_yukle():
    try:
        if os.path.exists(VERITABANI_DOSYASI):
            with open(VERITABANI_DOSYASI, "r", encoding="utf-8") as f:
                veri = json.load(f)
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
        with open(VERITABANI_DOSYASI, "w", encoding="utf-8") as f:
            json.dump(veri, f, ensure_ascii=False, indent=4)
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

def yerel_mantik_ozetleyici(metin, madde_sayisi=5):
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
    durma_kelimeleri = {"ve", "veya", "ama", "fakat", "ile", "bir", "bu", "için", "gibi", "da", "de", "the", "and"}
    
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

def video_analiz_proses_et(metin, limit):
    if not isinstance(metin, str) or len(metin.strip()) < 15:
        st.error("❌ Belirtilen videoya ait transkript akışı boş veya çok kısa.")
        return
        
    ham_maddeler = yerel_mantik_ozetleyici(metin, madde_sayisi=limit)
    ozet_maddeleri = [f"📌 {m}" for m in ham_maddeler]
    simdi = datetime.now()
    veri_paketi = {"tarih": simdi.strftime("%d.%m.%Y"), "saat": simdi.strftime("%H:%M:%S"), "metin": metin, "ozet": ozet_maddeleri}
    gecmis_ekle(veri_paketi)
    st.session_state["aktif_ozet"] = veri_paketi

def otomatik_url_transkript_motoru(video_id):
    """
    Sadece URL kullanarak 3 kademeli (Yerel Modül -> CDN Ayna 1 -> CDN Ayna 2)
    kesintisiz otomatik veri çekme hattı.
    """
    # 1. KADEME: Resmi Python Yapısı (En hızlı ve güvenli yol)
    try:
        altyazi_listesi = YouTubeTranscriptApi.get_transcript(video_id, languages=['tr', 'en'])
        metin = " ".join([parca['text'] for parca in altyazi_listesi])
        if len(metin.strip()) > 50:
            return metin
    except Exception as e:
        pass

    # Sunucu başlık tanımlamaları
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "Accept": "application/json"
    }

    # 2. KADEME: Yedek Küresel Dağıtık CDN Hattı
    try:
        url_yedek1 = f"https://v0.lat{video_id}"
        req1 = urllib.request.Request(url_yedek1, headers=headers)
        with urllib.request.urlopen(req1, timeout=6) as response1:
            veri = json.loads(response1.read().decode("utf-8"))
            if isinstance(veri, list):
                metin = " ".join([item.get("text", "") for item in veri if item.get("text")])
                if len(metin.strip()) > 50: return metin
    except:
        pass

    # 3. KADEME: Son Çare Küresel API Ağ Geçidi
    try:
        url_yedek2 = f"https://yt-api.com{video_id}"
        req2 = urllib.request.Request(url_yedek2, headers=headers)
        with urllib.request.urlopen(req2, timeout=6) as response2:
            veri = json.loads(response2.read().decode("utf-8"))
            if isinstance(veri, dict) and "transcript" in veri:
                return veri["transcript"]
    except:
        pass

    return None

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

# --- ANA SAYFA PANELİ ---
st.title("📺 AI Akıllı Video & Metin Yorumlayıcı SaaS")
st.write("Gelişmiş İstatistik Paneli ve Kesintisiz Çözüm Altyapısı")
st.divider()

madde_limiti = st.slider("Çıkarılacak Kritik Madde Sayısı:", min_value=3, max_value=15, value=5, step=1)

st.subheader("📺 1. Mod: YouTube Video Analizi")
video_linki = st.text_input("YouTube Linki veya Kodu Girin:", value="", placeholder="https://youtube.com...", key="main_yt_box")

if st.button("🚀 Videoyu Saniyeler İçinde Yorumla", key="main_yt_btn"):
    if not video_linki.strip():
        st.warning("Lütfen bir YouTube linki girin.")
    else:
        v_id = youtube_id_bul_kesin(video_linki)
        
        with st.spinner("🔄 Gelişmiş veri tünelleri optimize ediliyor... Transkript otomatik olarak indiriliyor..."):
            gelen_veri = otomatik_url_transkript_motoru(v_id)
            
        if gelen_veri:
            video_analiz_proses_et(gelen_veri, madde_limiti)
            st.success("🎉 Video verileri başarıyla çözümlendi! Kritik maddeler aşağıda listelenmiştir.")
            st.rerun()
        else:
            st.error("❌ Bu videonun transkript katmanına otomatik olarak erişilemedi. Lütfen videonun herkese açık olduğundan ve altyazı seçeneğinin aktif olduğundan emin olun.")

st.divider()

st.subheader("📝 2. Mod: Doğrudan Metin Analizi")
girilen_metin = st.text_area("Yorumlanacak Herhangi Bir Uzun Metni Yapıştırın:", height=150, key="main_text_box")
if st.button("⚡ Metni Analiz Et", key="main_text_btn"):
    if not girilen_metin.strip():
        st.warning("Lütfen metin girin.")
    else:
        ham_maddeler = yerel_mantik_ozetleyici(girilen_metin)
        ozet_maddeleri = [f"💡 {m}" for m in ham_maddeler[:madde_limiti]]
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
        t_fmt = f"--- AI ANALIZ RAPORU ---\nTarih: {g.get('tarih','')}\n\nKritik Maddeler:\n"
        for m in g.get('ozet', []): t_fmt += f"{m}\n"
        st.download_button(label="📥 TXT Olarak İndir", data=t_fmt.encode('utf-8'), file_name="analiz.txt", mime="text/plain", key="down_btn")
