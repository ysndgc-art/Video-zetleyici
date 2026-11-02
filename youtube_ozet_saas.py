import streamlit as st
import json
import os
import re
import urllib.request
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

def evrensel_json_metin_ayristirici(veri_objesi):
    """
    API'lerden gelen karmaşık, iç içe geçmiş veya zaman damgalı JSON objelerini 
    derinlemesine tarayarak saf transkript metnine dönüştüren evrensel tarayıcı.
    """
    parcalar = []
    
    # Senaryo 1: Doğrudan liste formatı (Düz metin dizileri veya sözlük listesi)
    if isinstance(veri_objesi, list):
        for item in veri_objesi:
            if isinstance(item, str):
                parcalar.append(item)
            elif isinstance(item, dict):
                # 'text', 'text_val', 'line' gibi popüler tüm anahtarları kontrol et
                for key in ["text", "text_val", "line", "transcript", "data"]:
                    if key in item and item[key]:
                        parcalar.append(str(item[key]))
                        break
                        
    # Senaryo 2: Gelişmiş anahtarlı sözlük yapısı (yt-api veya kompleks yapılar)
    elif isinstance(veri_objesi, dict):
        if "transcript" in veri_objesi and isinstance(veri_objesi["transcript"], str):
            return veri_objesi["transcript"].strip()
            
        # İç içe geçmiş veri listelerini (data, lines, segments) tara
        for root_key in ["data", "lines", "segments", "transcript", "subtitles"]:
            if root_key in veri_objesi:
                alt_veri = veri_objesi[root_key]
                if isinstance(alt_veri, list):
                    for sub_item in alt_veri:
                        if isinstance(sub_item, dict) and "text" in sub_item:
                            parcalar.append(str(sub_item["text"]))
                        elif isinstance(sub_item, str):
                            parcalar.append(sub_item)
                elif isinstance(alt_veri, str):
                    return alt_veri.strip()
                    
    temiz_sonuc = " ".join(parcalar).strip()
    return temiz_sonuc if len(temiz_sonuc) > 30 else None

def sunucu_tarafli_kesintisiz_transkript_motoru(video_id):
    """
    CORS kısıtlamalarından muaf, evrensel veri ayıklayıcı entegreli 
    kesintisiz Python tünel motoru.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
        "Accept": "application/json",
        "Origin": "https://youtube.com",
        "Referer": "https://youtube.com/"
    }
    
    # Küresel deşifre ağ geçitleri (Doğru endpoint eğik çizgileri entegre edildi)
    endpoints = [
        f"https://v0.lat{video_id}",
        f"https://yt-api.com{video_id}",
        f"https://v0.lat{video_id}"
    ]
    
    for url in endpoints:
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=8) as response:
                ham_veri = response.read().decode("utf-8")
                if not ham_veri.strip():
                    continue
                    
                veri_objesi = json.loads(ham_veri)
                cozulen_metin = evrensel_json_metin_ayristirici(veri_objesi)
                
                if cozulen_metin:
                    return cozulen_metin
        except:
            continue
            
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
st.write("Evrensel Veri Şeması Çözücü Altyapısı ile Kesintisiz URL Otomasyonu")
st.divider()

madde_limiti = st.slider("Çıkarılacak Kritik Madde Sayısı:", min_value=3, max_value=15, value=5, step=1)

st.subheader("📺 1. Mod: YouTube Video Analizi")
video_linki = st.text_input("YouTube Linki veya Kodu Girin:", value="", placeholder="https://youtube.com/watch?v=...", key="main_yt_box")

if st.button("🚀 Videoyu Saniyeler İçinde Yorumla", key="main_yt_btn"):
    if not video_linki.strip():
        st.warning("Lütfen bir YouTube linki girin.")
    else:
        v_id = youtube_id_bul_kesin(video_linki)
        
        with st.spinner("🔄 Gelişmiş veri şemaları çözümleniyor... Güvenli sunucu ağ geçidi üzerinden transkript indiriliyor..."):
            gelen_veri = sunucu_tarafli_kesintisiz_transkript_motoru(v_id)
            
        if gelen_veri:
            ham_maddeler = yerel_mantik_ozetleyici(gelen_veri, madde_sayisi=madde_limiti)
            ozet_maddeleri = [f"📌 {m}" for m in ham_maddeler]
            simdi = datetime.now()
            veri_paketi = {
                "tarih": simdi.strftime("%d.%m.%Y"), 
                "saat": simdi.strftime("%H:%M:%S"), 
                "metin": gelen_veri, 
                "ozet": ozet_maddeleri
            }
            gecmis_ekle(veri_paketi)
            st.session_state["aktif_ozet"] = veri_paketi
            st.success("🎉 Video verileri başarıyla çözümlendi!")
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
        ham_maddeler = yerel_mantik_ozetleyici(girilen_metin, madde_sayisi=madde_limiti)
        ozet_maddeleri = [f"💡 {m}" for m in ham_maddeler]
        simdi = datetime.now()
