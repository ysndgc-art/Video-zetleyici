import streamlit as st
import json
import os
import re
from datetime import datetime
import yt_dlp

# --- SAYFA YAPILANDIRMASI ---
st.set_page_config(page_title="AI Video & Metin Analiz SaaS", page_icon="📺", layout="wide")

VERITABANI_DOSYASI = "ozet_gecmisi.json"

def veritabani_yukle():
    try:
        if os.path.exists(VERITABANI_DOSYASI):
            with open(VERITABANI_DOSYASI, "r", encoding="utf-8") as f:
                return json.load(f)
    except:
        pass
    return []

def veritabani_kaydet(yeni_ozet):
    try:
        gecmis = veritabani_yukle()
        if not any(g.get('metin', '')[:30] == yeni_ozet['metin'][:30] for g in gecmis if 'metin' in g):
            gecmis.insert(0, yeni_ozet)
            with open(VERITABANI_DOSYASI, "w", encoding="utf-8") as f:
                json.dump(gecmis, f, ensure_ascii=False, indent=4)
    except:
        pass

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

# --- 🧠 %100 YEREL GELİŞMİŞ ANALİZ MOTORU ---
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
        'ie_key': 'Youtube'
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
            indirilen_dil = "en" if ".en." in bulunan_dosya else "tr"
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
            
            return " ".join(temiz_satirlar), indirilen_dil
    except:
        pass
    return None, "tr"

# --- SIDEBAR ---
st.sidebar.title("📜 Analiz Geçmişiniz")
gecmis = veritabani_yukle()
if gecmis:
    for sira, g in enumerate(gecmis[:10]):
        if st.sidebar.button(f"⏱️ {g.get('saat','')} - {g.get('metin','')[:15]}...", key=f"hist_{sira}"):
            st.session_state["aktif_ozet"] = g
else:
    st.sidebar.info("Henüz geçmiş analiz bulunmuyor.")

st.sidebar.divider()
if st.sidebar.button("🗑️ Geçmişi Temizle"):
    if os.path.exists(VERITABANI_DOSYASI):
        try: os.remove(VERITABANI_DOSYASI)
        except: pass
    st.sidebar.success("Geçmiş silindi!")
    st.rerun()

# --- ANA SAYFA ---
st.title("📺 AI Akıllı Video & Metin Yorumlayıcı SaaS")
st.write("Sıfır Girinti Riski, Maksimum Kararlılık Yapısı Aktif")
st.divider()

if "aktif_ozet" in st.session_state and st.session_state["aktif_ozet"]:
    st.info("📂 **Geçmiş Analiz Görüntüleniyor**")
    g = st.session_state["aktif_ozet"]
    st.success(f"✅ Analiz Tarihi: {g.get('tarih','')} - {g.get('saat','')}")
    for m in g.get('ozet', []): 
        st.write(m)
    if st.button("➕ Yeni Analiz Ekranına Dön"):
        st.session_state["aktif_ozet"] = None
        st.rerun()
    st.stop()

mod = st.radio("Mod Seçin:", ["📺 YouTube Videosu", "📝 Uzun Metin"], horizontal=True)
madde_limiti = st.select_slider("Çıkarılacak Kritik Madde Sayısı:", options=[5, 10, 15], value=5)

# --- 📺 YOUTUBE MODU İŞLEMLERİ ---
if mod == "📺 YouTube Videosu":
    video_linki = st.text_input("YouTube Linki veya Kodu Girin:", value="", placeholder="Örn: https://youtube.com...", key="video_url_girdisi")
    
    if st.button("Videoyu Analiz Et"):
        if not video_linki.strip():
            st.warning("Lütfen analiz etmek için geçerli bir YouTube URL'si veya video kodu girin.")
        else:
            st.cache_data.clear()
            v_id = youtube_id_bul_kesin(video_linki)
            PROJE_DIZINI = os.path.dirname(os.path.abspath(__file__))
            CEREZ_YOLU = os.path.join(PROJE_DIZINI, "www.youtube.com_cookies.txt")
            
            with st.spinner("📥 Yeni videonun altyazıları indiriliyor..."):
                metin, altyazi_dili = ytdlp_altyazi_cek(v_id, CEREZ_YOLU)
                
            if not metin:
                st.error("Altyazı indirilemedi. Girdiğiniz linkin doğruluğundan ve videonun altyazı içerdiğinden emin olun.")
            else:
                with st.spinner(f"🤖 Yapay zeka yeni girdi için {madde_limiti} kritik maddeyi yapılandırıyor..."):
                    ham_maddeler = yerel_mantik_ozetleyici(metin, madde_sayisi=madde_limiti, dil=altyazi_dili)
                    emojiler = ["📌", "📊", "💡", "⚙️", "🎯", "🚀", "🔑", "💎", "📣", "📝", "🧠", "🔥", "⚡", "🍀", "🎯"]
                    ozet_maddeleri = [f"{emojiler[i % len(emojiler)]} {m}" for i, m in enumerate(ham_maddeler)]
                    tum_maddeler_metin = "\n".join([f"- {m}" for m in ham_maddeler])
                    
                simdi = datetime.now()
                veritabani_kaydet({"tarih": simdi.strftime("%d.%m.%Y"), "saat": simdi.strftime("%H:%M:%S"), "metin": metin, "ozet": ozet_maddeleri})
                
                st.success(f"✅ {madde_limiti} Maddelik Yeni Analiz Başarıyla Tamamlandı!")
                for madde in ozet_maddeleri:
                    st.write(madde)
                    
                if altyazi_dili == "en":
                    st.divider()
                    st.info("💡 İngilizce içerik saptandı. Aşağıdaki butona tıklayarak maddeleri Google Translate ile hızlıca Türkçe'ye çevirebilirsiniz:")
                    st.markdown(f'<a href="https://google.com" target="_blank" style="display:inline-block; background-color:#2cbd5d; color:white; padding:10px 20px; border-radius:6px; text-decoration:none; font-weight:bold;">🌐 Google Translate Sayfasını Aç</a>', unsafe_allow_html=True)
                    st.text_area("📋 Kopyalanacak Maddeler:", value=tum_maddeler_metin, height=120)
                    
                with st.expander("📝 İşlenen Ham Kaynak Metni Görüntüle"):
                    st.caption(metin)

# --- 📝 METİN MODU İŞLEMLERİ ---
if mod == "📝 Uzun Metin":
    girilen_metin = st.text_area("Yorumlanacak Uzun Metni Girin:", height=200, key="metin_alan_girdisi")
    
    if st.button("Metni Analiz Et"):
        if not girilen_metin.strip():
            st.warning("Metin alanı boş bırakılamaz.")
        else:
            with st.spinner(f"🤖 Süzgeç çalışıyor ({madde_limiti} Madde)..."):
                ham_maddeler = yerel_mantik_ozetleyici(girilen_metin, madde_sayisi=madde_limiti, dil="tr")
