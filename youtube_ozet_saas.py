import streamlit as st
import json
import os
import re
from datetime import datetime
import yt_dlp

# --- SAYFA YAPILANDIRMASI ---
st.set_page_config(page_title="AI Video & Metin Analiz SaaS", page_icon="📺", layout="wide")

VERITABANI_DOSYASI = "ozet_gecmisi.json"
GUNLUK_UCRETSIZ_LIMIT = 10

def veritabani_yukle():
    try:
        if os.path.exists(VERITABANI_DOSYASI):
            with open(VERITABANI_DOSYASI, "r", encoding="utf-8") as f:
                veri = json.load(f)
                if isinstance(veri, list):
                    return {"gecmis": veri, "kota": {}}
                if isinstance(veri, dict) and "gecmis" in veri:
                    return veri
    except:
        pass
    return {"gecmis": [], "kota": {}}

def veritabani_kaydet(veri):
    try:
        with open(VERITABANI_DOSYASI, "w", encoding="utf-8") as f:
            json.dump(veri, f, ensure_ascii=False, indent=4)
    except:
        pass

def kota_kontrol_ve_guncelle():
    veri = veritabani_yukle()
    if not isinstance(veri, dict) or "kota" not in veri:
        veri = {"gecmis": [], "kota": {}}
    bugun = datetime.now().strftime("%d.%m.%Y")
    mevcut_kota = veri["kota"].get(bugun, 0)
    if mevcut_kota >= GUNLUK_UCRETSIZ_LIMIT:
        return False, mevcut_kota
    veri["kota"][bugun] = mevcut_kota + 1
    veritabani_kaydet(veri)
    return True, mevcut_kota + 1

def gecmis_ekle(yeni_ozet):
    veri = veritabani_yukle()
    if not isinstance(veri, dict) or "gecmis" not in veri:
        veri = {"gecmis": [], "kota": {}}
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

def ytdlp_altyazi_cek(video_id, cerez_yolu):
    safe_id = str(video_id).strip()
    ydl_opts = {
        'writesubtitles': True,
        'writeautomaticsub': True,
        'subtitleslangs': ['tr', 'en', 'auto', 'tr-orig', 'en-orig', '.*'],
        'skip_download': True,
        'cookiefile': cerez_yolu if os.path.exists(cerez_yolu) else None,
        'outtmpl': f"sub_{safe_id}",
        'quiet': True,
        'no_warnings': True,
        'ie_key': 'Youtube',
        'socket_timeout': 20,
        'retries': 3,
        # 🤖 Bot Engellemesini Aşmak İçin Gelişmiş İstemci Maskelemeleri
        'extractor_args': {
            'youtube': {
                'clients': ['web', 'mweb', 'tv', 'android'],
                'skip': ['dash', 'hls']
            }
        },
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7'
        }
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([safe_id])
        bulunan_dosya = None
        # VTT, SRT ve diğer altyazi uzantılarını tarama listesine dahil et
        for dosya in os.listdir("."):
            if dosya.startswith(f"sub_{safe_id}") and any(dosya.endswith(ext) for ext in [".vtt", ".srt", ".ttml", ".srv3"]):
                bulunan_dosya = dosya
                break
        if bulunan_dosya and os.path.exists(bulunan_dosya):
            indirilen_dil = "en" if ".en" in bulunan_dosya.lower() else "tr"
            with open(bulunan_dosya, "r", encoding="utf-8") as f:
                icerik = f.read()
            lines = icerik.split("\n")
            temiz_satirlar = []
            for line in lines:
                if "-->" not in line and line.strip() and not line.strip().isdigit() and "WEBVTT" not in line and "Kind:" not in line and "Language:" not in line:
                    clean_line = re.sub(r'<[^>]*>', '', line).strip()
                    if clean_line and (not temiz_satirlar or temiz_satirlar[-1] != clean_line):
                        temiz_satirlar.append(clean_line)
            try: os.remove(bulunan_dosya)
            except: pass
            if temiz_satirlar:
                return " ".join(temiz_satirlar), indirilen_dil
    except:
        pass
    return None, "tr"

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
kota_havuzu = veri_havuzu.get("kota", {})

if gecmis_listesi:
    for sira, g in enumerate(gecmis_listesi[:10]):
        if st.sidebar.button(f"⏱️ {g.get('saat','')} - {g.get('metin','')[:15]}...", key=f"hist_{sira}"):
            st.session_state["aktif_ozet"] = g
else:
    st.sidebar.info("Henüz geçmiş analiz bulunmuyor.")

# --- ANA SAYFA PANELİ ---
st.title("📺 AI Akıllı Video & Metin Yorumlayıcı SaaS")
st.write("Gelişmiş İstatistik Paneli ve Kolay Dışa Aktarma Sistemi")
st.divider()

mod = st.radio("Mod Seçin:", ["📺 YouTube Videosu", "📝 Uzun Metin"], horizontal=True)
madde_limiti = st.slider("Çıkarılacak Kritik Madde Sayısı:", min_value=3, max_value=15, value=5, step=1)

if mod == "📺 YouTube Videosu":
    video_linki = st.text_input("YouTube Linki veya Kodu Girin:", value="", placeholder="Örn: https://youtube.com...")
    if st.button("Videoyu Analiz Et"):
        if not video_linki.strip():
            st.warning("Lütfen bir YouTube linki girin.")
        else:
            izin_verildi, _ = kota_kontrol_ve_guncelle()
            if not izin_verildi:
                st.error("❌ Günlük ücretsiz limite ulaştınız.")
            else:
                v_id = youtube_id_bul_kesin(video_linki)
                PROJE_DIZINI = os.path.dirname(os.path.abspath(__file__))
                CEREZ_YOLU = os.path.join(PROJE_DIZINI, "www.youtube.com_cookies.txt")
                
                with st.spinner("📥 Altyazılar indiriliyor..."):
                    metin, altyazi_dili = ytdlp_altyazi_cek(v_id, CEREZ_YOLU)
                    
                if not metin:
                    st.error("YouTube sunucularından altyazı çekilemedi. Video gizli olabilir veya altyazı içermiyor olabilir.")
                else:
                    with st.spinner("🤖 Yapay zeka maddeleri çıkarıyor..."):
                        ham_maddeler = yerel_mantik_ozetleyici(metin, madde_sayisi=madde_limiti, dil=altyazi_dili)
                        ozet_maddeleri = [f"📌 {m}" for m in ham_maddeler]
                    simdi = datetime.now()
                    veri_paketi = {"tarih": simdi.strftime("%d.%m.%Y"), "saat": simdi.strftime("%H:%M:%S"), "metin": metin, "ozet": ozet_maddeleri}
                    gecmis_ekle(veri_paketi)
                    st.session_state["aktif_ozet"] = veri_paketi
                    st.rerun()

if mod == "📝 Uzun Metin":
    girilen_metin = st.text_area("Yorumlanacak Uzun Metni Girin:", height=200)
    if st.button("Metni Analiz Et"):
        if not girilen_metin.strip():
