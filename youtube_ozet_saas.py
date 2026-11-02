import streamlit as st
import json
import os
import re
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime

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

def engelsiz_resmi_yol_ile_altyazi_cek(video_id):
    """
    YouTube'un ham video sayfalarındaki gömülü altyazı manifestolarını 
    gerçekçi tarayıcı taklidi başlıklarıyla ayıklar ve bot korumasını geçer.
    """
    # Gerçek bir masaüstü tarayıcısının HTTP kimliği taklit edilir
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache"
    }
    
    try:
        # 1. Adım: Video sayfasına gerçekçi kimlikle git ve altyazı izlerini (timedtext) ara
        video_url = f"https://youtube.com{video_id}"
        req = urllib.request.Request(video_url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as response:
            html = response.read().decode("utf-8")
            
        # YouTube oynatıcı verilerinin içerisindeki timedtext URL'lerini bul
        match = re.search(r'https://youtube.com[^\s"]+', html)
        if not match:
            # Alternatif eşleşme araması yap (Kaçış karakterli URL'ler için)
            match = re.search(r'https:\\/\\/://youtube.com\\/api\\/timedtext[^"\s]+', html)
            
        if match:
            raw_url = match.group(0)
            # URL içerisindeki JSON/Unicode kaçış karakterlerini temizle ve formatla
            clean_url = raw_url.replace(r'\/', '/').replace('\\u0026', '&').replace('&amp;', '&')
            
            # Parametreleri manipüle et: Varsayılan dil olarak Türkçe veya otomatik çeviri zorla
            if "lang=tr" not in clean_url:
                clean_url += "&lang=tr&fmt=srv1"
            else:
                clean_url = re.sub(r'fmt=[^&]+', 'fmt=srv1', clean_url)
                
            # 2. Adım: Ayıklanan resmi XML altyazı kaynağını doğrudan güvenli kanaldan çek
            req_xml = urllib.request.Request(clean_url, headers=headers)
            with urllib.request.urlopen(req_xml, timeout=10) as xml_response:
                xml_data = xml_response.read().decode("utf-8")
                
            # XML verisini ayrıştır ve konuşma metinlerini birleştir
            if xml_data.strip() and "<text" in xml_data:
                root = ET.fromstring(xml_data)
                parcalar = [t.text for t in root.findall(".//text") if t.text]
                if parcalar:
                    # HTML entity kodlarını (&amp;, &quot; vb.) düzeltmek için basit temizlik
                    metin = " ".join(parcalar)
                    metin = metin.replace("&amp;", "&").replace("&quot;", '"').replace("&#39;", "'")
                    return metin
    except Exception as e:
        pass
        
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
        
        with st.spinner("🔄 Anti-bot bariyerleri aşılıyor... Doğrudan YouTube resmi veri katmanından transkript çözümleniyor..."):
            gelen_veri = engelsiz_resmi_yol_ile_altyazi_cek(v_id)
            
        if gelen_veri:
            video_analiz_proses_et(gelen_veri, madde_limiti)
            st.success("🎉 Video verileri başarıyla çözümlendi! Kritik maddeler aşağıda listelenmiştir.")
            st.rerun()
        else:
            st.error("❌ Bu videonun transkript katmanına doğrudan erişilemedi. Lütfen videonun herkese açık olduğundan ve altyazı seçeneğinin (otomatik veya manuel) aktif olduğundan emin olun.")

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
