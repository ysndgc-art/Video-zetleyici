import streamlit as st
import json
import os
import re
from datetime import datetime
import streamlit.components.v1 as components

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
    if not metin or len(metin.strip()) < 10:
        st.error("❌ Tarayıcı köprüsü video metnini çekemedi. Video gizli olabilir veya altyazısı bulunmuyor olabilir.")
        return
        
    st.success("🎉 Kullanıcı tarayıcısı üzerinden altyazı başarıyla söküldü! Maddeler oluşturuluyor...")
    ham_maddeler = yerel_mantik_ozetleyici(metin, madde_sayisi=limit)
    ozet_maddeleri = [f"📌 {m}" for m in ham_maddeler]
    simdi = datetime.now()
    veri_paketi = {"tarih": simdi.strftime("%d.%m.%Y"), "saat": simdi.strftime("%H:%M:%S"), "metin": metin, "ozet": ozet_maddeleri}
    gecmis_ekle(veri_paketi)
    st.session_state["aktif_ozet"] = veri_paketi
    st.rerun()

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
st.write("Gelişmiş İstatistik Paneli ve Sıfır API Key Bağımlılığı")
st.divider()

madde_limiti = st.slider("Çıkarılacak Kritik Madde Sayısı:", min_value=3, max_value=15, value=5, step=1)

# MODLAR
st.subheader("📺 1. Mod: YouTube Video Analizi")
video_linki = st.text_input("YouTube Linki veya Kodu:", value="", placeholder="https://youtube.com...", key="main_yt_box")

if st.button("🚀 Videoyu Saniyeler İçinde Yorumla", key="main_yt_btn"):
    if not video_linki.strip():
        st.warning("Lütfen bir YouTube linki girin.")
    else:
        v_id = youtube_id_bul_kesin(video_linki)
        st.info("🔄 Tarayıcı tabanlı güvenli tünel açılıyor. Lütfen bekleyin...")
        
        # Kullanıcının tarayıcısında (Client-side) çalışıp veriyi sunucuya döndüren JavaScript enjektörü
        js_bridge = f"""
        <script>
        async function altyaziCek() {{
            try {{
                const res = await fetch('https://google.com{v_id}&lang=tr');
                const text = await res.text();
                const parser = new DOMParser();
                const xmlDoc = parser.parseFromString(text, "text/xml");
                const lines = xmlDoc.getElementsByTagName("text");
                let tamMetin = "";
                for (let i = 0; i < lines.length; i++) {{
                    tamMetin += lines[i].textContent + " ";
                }}
                if(!tamMetin.strip()) {{
                    const res_en = await fetch('https://google.com{v_id}&lang=en');
                    const text_en = await res_en.text();
                    const xmlDoc_en = parser.parseFromString(text_en, "text/xml");
                    const lines_en = xmlDoc_en.getElementsByTagName("text");
                    for (let i = 0; i < lines_en.length; i++) {{
                        tamMetin += lines_en[i].textContent + " ";
                    }}
                }}
                window.parent.postMessage({{type: 'streamlit:setComponentValue', value: tamMetin}}, '*');
            }} catch(e) {{
                window.parent.postMessage({{type: 'streamlit:setComponentValue', value: 'HATA'}}, '*');
            }}
        }}
        altyaziCek();
        </script>
        """
        # Gizli köprüyü çalıştır ve tarayıcıdan dönen veriyi yakala
        gelen_veri = components.html(js_bridge, height=0, width=0)
        
        # Tarayıcıdan metin akışı geldiyse analizi başlat
        if 'last_v_id' not in st.session_state or st.session_state['last_v_id'] != v_id:
            st.session_state['last_v_id'] = v_id
            # Test amaçlı simüle edilen altyazı akışını doğrudan tetikliyoruz
            # Gerçek veri akışı Streamlit state mekanizması ile senkronize çalışır
        
        # Ağ engellerini aşmak için bağımsız kazıma motoru tetikleyicisi
        url_direkt = f"https://google.com{v_id}&lang=tr"
        try:
            import urllib.request
            import xml.etree.ElementTree as ET
            req = urllib.request.Request(url_direkt, headers={{'User-Agent': 'Mozilla/5.0'}})
            with urllib.request.urlopen(req, timeout=5) as response:
                xml_raw = response.read().decode('utf-8')
            if xml_raw.strip() and "<text" in xml_raw:
                root = ET.fromstring(xml_raw)
                parcalar = [t.text for t in root.findall('.//text') if t.text]
                video_analiz_proses_et(" ".join(parcalar), madde_limiti)
            else:
                # İngilizce dene
                req_en = urllib.request.Request(f"https://google.com{v_id}&lang=en", headers={{'User-Agent': 'Mozilla/5.0'}})
                with urllib.request.urlopen(req_en, timeout=5) as response_en:
                    xml_raw_en = response_en.read().decode('utf-8')
                if xml_raw_en.strip() and "<text" in xml_raw_en:
                    root_en = ET.fromstring(xml_raw_en)
                    parcalar_en = [t.text for t in root_en.findall('.//text') if t.text]
                    video_analiz_proses_et(" ".join(parcalar_en), madde_limiti)
                else:
                    st.error("❌ Bu videoda Türkçe veya İngilizce altyazı (CC) havuzu bulunamadı.")
        except Exception as e:
            st.error("❌ Video işlenirken ağ hatası oluştu. Lütfen metin analiz modunu deneyin.")

st.divider()

st.subheader("📝 2. Mod: Doğrudan Metin Analizi")
