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
                return json.load(f)
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

# --- 📥 EVRENSEL DIŞA AKTARMA FORMATLARI MOTORU ---
def rapor_formatlarini_uret(tarih, saat, maddeler, baslik_url=""):
    # TXT Formati
    txt_cikisi = f"--- AI ANALIZ RAPORU ---\nTarih: {tarih} - {saat}\n"
    if baslik_url:
        txt_cikisi += f"Kaynak: {baslik_url}\n"
    txt_cikisi += "\nKritik Maddeler:\n"
    for m in maddeler:
        txt_cikisi += f"{m}\n"
        
    # Markdown Formati
    md_cikisi = f"# 📺 AI Akıllı Analiz Raporu\n\n- **Tarih:** {tarih} - {saat}\n"
    if baslik_url:
        md_cikisi += f"- **Kaynak:** [{baslik_url}]({baslik_url})\n"
    md_cikisi += "\n## 🔑 Çıkarılan Kritik Maddeler\n\n"
    for m in maddeler:
        md_cikisi += f"* {m}\n"
    md_cikisi += "\n---\n*AI Video & Metin Yorumlayıcı SaaS tarafından üretilmiştir.*"

    # HTML/Evrensel Yazdırılabilir PDF Formati (Streamlit için en kararlı yöntem)
    html_cikisi = f"""
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: Arial, sans-serif; padding: 30px; color: #333; }}
            h1 {{ color: #ff4b4b; border-bottom: 2px solid #eee; padding-bottom: 10px; }}
            .meta {{ color: #666; margin-bottom: 20px; font-size: 14px; }}
            ul {{ line-height: 1.6; }}
            li {{ margin-bottom: 12px; font-size: 16px; }}
        </style>
    </head>
    <body>
        <h1>📺 AI Akıllı Analiz Raporu</h1>
        <div class="meta">
            <strong>Tarih:</strong> {tarih} - {saat}<br>
            {"<strong>Kaynak:</strong> " + baslik_url if baslik_url else ""}
        </div>
        <h3>🔑 Çıkarılan Kritik Maddeler</h3>
        <ul>
    """
    for m in maddeler:
        html_cikisi += f"<li>{m}</li>"
    html_cikisi += """
        </ul>
    </body>
    </html>
    """
    return txt_cikisi, md_cikisi, html_cikisi

# --- SIDEBAR ---
st.sidebar.title("📜 Analiz Geçmişiniz")
veri_havuzu = veritabani_yukle()
gecmis_listesi = veri_havuzu.get("gecmis", []) if isinstance(veri_havuzu, dict) else []
kota_havuzu = veri_havuzu.get("kota", {}) if isinstance(veri_havuzu, dict) else []

if gecmis_listesi:
    for sira, g in enumerate(gecmis_listesi[:10]):
        if st.sidebar.button(f"⏱️ {g.get('saat','')} - {g.get('metin','')[:15]}...", key=f"hist_{sira}"):
            st.session_state["aktif_ozet"] = g
else:
    st.sidebar.info("Henüz geçmiş analiz bulunmuyor.")

st.sidebar.divider()

# KOTA GÖSTERGE PANELİ
bugun_str = datetime.now().strftime("%d.%m.%Y")
bugunku_kullanim = kota_havuzu.get(bugun_str, 0)
st.sidebar.subheader("📊 Günlük Kullanım Kotası")
st.sidebar.write(f"Bugün Kullanılan: **{bugunku_kullanim} / {GUNLUK_UCRETSIZ_LIMIT}**")
kalan_hak = GUNLUK_UCRETSIZ_LIMIT - bugunku_kullanim
if kalan_hak > 0:
    st.sidebar.success(f"🔓 {kalan_hak} adet ücretsiz analiz hakkınız kaldı.")
else:
    st.sidebar.error("⚠️ Günlük ücretsiz limitiniz doldu! Ek analizler ücrete tabidir.")

if st.sidebar.button("🗑️ Geçmişi Temizle"):
    if os.path.exists(VERITABANI_DOSYASI):
        try: os.remove(VERITABANI_DOSYASI)
        except: pass
    st.sidebar.success("Geçmiş silindi!")
    st.rerun()

# --- ANA SAYFA ---
st.title("📺 AI Akıllı Video & Metin Yorumlayıcı SaaS")
st.write("Gelişmiş İstatistik Paneli ve PDF / Markdown / TXT Dışa Aktarma Destekli Sürüm")
st.divider()

if "aktif_ozet" in st.session_state and st.session_state["aktif_ozet"]:
    st.info("📂 **Geçmiş Analiz Görüntüleniyor**")
    g = st.session_state["aktif_ozet"]
    st.success(f"✅ Analiz Tarihi: {g.get('tarih','')} - {g.get('saat','')}")
    
    for m in g.get('ozet', []): 
        st.write(m)
        
    st.divider()
    st.subheader("📥 Raporu Farklı Formatlarda İndir")
    
    t_fmt, m_fmt, h_fmt = rapor_formatlarini_uret(g.get('tarih',''), g.get('saat',''), g.get('ozet', []))
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.download_button(label="📥 TXT Olarak İndir", data=t_fmt.encode('utf-8'), file_name=f"analiz_{g.get('saat','')}.txt", mime="text/plain")
