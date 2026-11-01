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

# --- 🌐 %100 YEREL (OFFLINE) SÖZLÜKSEL ÇEVİRİ MOTORU ---
def yerel_sozluk_cevirisi(madde_listesi):
    # Dış API'ler kilitlendiğinde Streamlit'in kendi hafızasından çalışan akıllı sözlük
    sozluk = {
        "the": "", "and": "ve", "to": "-e", "of": "ait", "a": "bir", "in": "içinde", "is": "dır", "that": "şu",
        "it": "o", "was": "idi", "for": "için", "on": "üzerinde", "are": "dırlar", "as": "olarak", "with": "ile",
        "this": "bu", "they", "onlar", "but": "ama", "what": "ne", "from": "-den", "your": "senin", "how": "nasıl",
        "video": "video", "channel": "kanal", "subscribe": "abone ol", "like": "beğen", "music": "müzik",
        "important": "önemli", "first": "ilk", "second": "ikinci", "step": "adım", "code": "kod", "system": "sistem",
        "project": "proje", "software": "yazılım", "problem": "sorun", "error": "hata", "success": "başarı",
        "learning": "öğrenme", "data": "veri", "development": "geliştirme", "application": "uygulama",
        "we": "biz", "you": "siz", "he": "o", "she": "o", "can": "-ebilir", "will": "-ecek", "should": "-meli",
        "good": "iyi", "bad": "kötü", "new": "yeni", "old": "eski", "make": "yapmak", "get": "almak", "see": "görmek"
    }
    
    cevirilmis_maddeler = []
    emojiler = ["📌", "📊", "💡", "⚙️", "🎯"]
    
    for i, madde in enumerate(madde_listesi):
        kelimeler = madde.split()
        yeni_cumle = []
        for k in kelimeler:
            temiz_k = re.sub(r'[^\w]', '', k).lower()
            # Sözlükte karşılığı varsa değiştir, yoksa orijinal kelimeyi koru
            if temiz_k in sozluk and sozluk[temiz_k] != "":
                # Noktalama işaretini koruyarak ekle
                ek = k.replace(re.sub(r'[^\w]', '', k), sozluk[temiz_k])
                yeni_cumle.append(ek)
            else:
                yeni_cumle.append(k)
                
        cumle_metni = " ".join(yeni_cumle).strip()
        cumle_metni = cumle_metni.upper() + cumle_metni[1:]
        cevirilmis_maddeler.append(f"{emojiler[i]} {cumle_metni}")
        
    return cevirilmis_maddeler

# --- 🧠 ÇOK DİLLİ GELİŞMİŞ YEREL ANALİZ MOTORU ---
def yerel_mantik_ozetleyici(metin, dil="tr"):
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

    if len(cumleler) <= 5:
        return [c for c in cumleler if len(c.split()) > 3]

    kelimeler = re.findall(r'\w+', temiz_metin.lower())
    if dil == "tr":
        durma_kelimeleri = {
            "ve", "veya", "ama", "fakat", "ile", "bir", "bu", "şu", "o", "da", "de", 
            "için", "gibi", "çok", "en", "daha", "olan", "olarak", "ki", "yani", "böyle",
            "şey", "şeyler", "her", "zaten", "bunu", "buna", "bunda", "merhaba", "arkadaşlar"
        }
    else:
        durma_kelimeleri = {
            "the", "and", "you", "that", "was", "for", "on", "are", "with", "as", "this",
            "they", "but", "what", "from", "about", "your", "hello", "guys"
        }
    
    frekanslar = {}
    for k in kelimeler:
        if k not in durma_kelimeleri and len(k) > 3:
            frekanslar[k] = frekanslar.get(k, 0) + 1

    cumle_puanlari = {}
    for idx, cumle in enumerate(cumleler):
        puan = 0
        kelime_listesi = re.findall(r'\w+', cumle.lower())
        if len(kelime_listesi) < 5 or len(kelime_listesi) > 25:
            continue
        for kelime in kelime_listesi:
            if kelime in frekanslar:
                puan += frekanslar[kelime]
        cumle_puanlari[idx] = puan

    if not cumle_puanlari:
        return [c for c in cumleler[:5]]

    en_iyi_indeksler = sorted(cumle_puanlari, key=cumle_puanlari.get, reverse=True)[:5]
    en_iyi_indeksler.sort()

    sonuc = []
    for idx in en_iyi_indeksler:
        ham_cumle = cumleler[idx].strip()
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
    except Exception:
        pass
    return None, "tr"

# --- BAĞIMSIZ MOD MODÜLLERİ ---
def youtube_modu_calistir():
    video_linki = st.text_input("YouTube Linki veya Kodu:", value="1OkydHdhABQ")
    if st.button("Videoyu Analiz Et"):
        v_id = youtube_id_bul_kesin(video_linki)
        PROJE_DIZINI = os.path.dirname(os.path.abspath(__file__))
        CEREZ_YOLU = os.path.join(PROJE_DIZINI, "www.youtube.com_cookies.txt")
        
        with st.spinner("📥 1. Adım: Altyazılar başarıyla indiriliyor..."):
            metin, altyazi_dili = ytdlp_altyazi_cek(v_id, CEREZ_YOLU)
            
        if not metin:
            st.error("Altyazı indirilemedi. Videonun altyazı içerdiğinden emin olun.")
            return
            
        with st.spinner("🤖 2. Adım: Kritik noktalar hesaplanıyor ve optimize ediliyor..."):
            ham_maddeler = yerel_mantik_ozetleyici(metin, dil=altyazi_dili)
            if altyazi_dili == "en":
                st.info("🌐 İngilizce içerik saptandı, hibrit güvenli çeviri devreye giriyor...")
                ozet_maddeleri = yerel_sozluk_cevirisi(ham_maddeler)
            else:
                emojiler = ["📌", "📊", "💡", "⚙️", "🎯"]
                ozet_maddeleri = [f"{emojiler[i]} {m}" for i, m in enumerate(ham_maddeler)]
            
        simdi = datetime.now()
        veritabani_kaydet({"tarih": simdi.strftime("%d.%m.%Y"), "saat": simdi.strftime("%H:%M:%S"), "metin": metin, "ozet": ozet_maddeleri})
        
        st.success("✅ Analiz Başarıyla Tamamlandı!")
        st.subheader("📊 Yapılandırılmış Kritik Özet Maddeleri:")
        for madde in ozet_maddeleri:
            st.write(madde)
        
        with st.expander("📝 İşlenen Ham Kaynak Metni Görüntüle"):
            st.caption(metin)

def metin_modu_calistir():
    girilen_metin = st.text_area("Özetlenecek Metni Girin:", height=200)
    if st.button("Metni Özetle"):
        if not girilen_metin.strip():
            st.warning("Metin alanı boş bırakılamaz.")
            return
            
        with st.spinner("🤖 Mantıksal süzgeç çalışıyor..."):
            ham_maddeler = yerel_mantik_ozetleyici(girilen_metin, dil="tr")
            emojiler = ["📌", "📊", "💡", "⚙️", "🎯"]
            ozet_maddeleri = [f"{emojiler[i]} {m}" for i, m in enumerate(ham_maddeler)]
            
        st.success("✅ İşlem Başarılı!")
        st.subheader("📊 Özet Maddeleri:")
        for madde in ozet_maddeleri:
            st.write(madde)

# --- SIDEBAR GEÇMİŞ ---
st.sidebar.title("📜 Özet Geçmişiniz")
gecmis = veritabani_yukle()
if gecmis:
    for sira, g in enumerate(gecmis[:10]):
