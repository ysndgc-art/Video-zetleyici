import streamlit as st
import json
import os
import time
from datetime import datetime
import re
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
import io
import urllib.request
import xml.etree.ElementTree as ET

# Web Sayfası Tasarımı
st.set_page_config(page_title="AI Video & Metin Özetleyici SaaS", page_icon="📺", layout="wide")

# --- VERİBATANI (JSON) FONKSİYONLARI ---
VERITABANI_DOSYASI = "ozet_gecmisi.json"

def veritabani_yukle():
    if os.path.exists(VERITABANI_DOSYASI):
        with open(VERITABANI_DOSYASI, "r", encoding="utf-8") as f:
            try: 
                return json.load(f)
            except: 
                return []
    return []

def veritabani_kaydet(yeni_ozet):
    gecmis = veritabani_yukle()
    if not any(g['metin'][:30] == yeni_ozet['metin'][:30] for g in gecmis):
        gecmis.insert(0, yeni_ozet)
        with open(VERITABANI_DOSYASI, "w", encoding="utf-8") as f:
            json.dump(gecmis, f, ensure_ascii=False, indent=4)

def youtube_id_bul_kesin(link_veya_id):
    girdi = link_veya_id.strip()
    if len(girdi) == 11 and not "/" in girdi and not "." in girdi:
        return girdi
    bulunan = re.findall(r'[a-zA-Z0-9_-]{11}', girdi)
    if bulunan:
        for parca in bulunan:
            if "youtube" not in parca.lower() and "youtu" not in parca.lower():
                return parca
    return None

# --- 🌐 YEREL ALTYAZI ÇEKİCİ (KÜTÜPHANESİZ GÜVENLİ MOTOR) ---
def yerel_altyazi_cek(video_id, cerez_yolu):
    try:
        # Netscape çerez formatından cookie string üretme
        cookie_list = []
        if os.path.exists(cerez_yolu):
            with open(cerez_yolu, "r", encoding="utf-8") as f:
                for line in f:
                    if not line.startswith("#") and line.strip():
                        parts = line.strip().split("\t")
                        if len(parts) >= 7:
                            cookie_list.append(f"{parts[5]}={parts[6]}")
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Cookie": "; ".join(cookie_list)
        }
        
        # Video sayfasını iste
        req = urllib.request.Request(f"https://youtube.com{video_id}", headers=headers)
        with urllib.request.urlopen(req, timeout=10) as response:
            html = response.read().decode('utf-8')
            
        # Altyazı URL'ini HTML içinden ayıkla
        match = re.search(r'"captionTracks":\s*\[(.*?)\]', html)
        if not match:
            return None
            
        tracks_json = json.loads(f"[{match.group(1)}]")
        
        # Türkçe veya İngilizce parça seç
        track_url = None
        for track in tracks_json:
            if track.get("languageCode") in ["tr", "en"]:
                track_url = track.get("baseUrl")
                break
        if not track_url:
            track_url = tracks_json[0].get("baseUrl")
            
        if not track_url:
            return None
            
        # XML formatındaki altyazıyı indir ve düz metne çevir
        req_track = urllib.request.Request(track_url, headers={"User-Agent": headers["User-Agent"]})
        with urllib.request.urlopen(req_track, timeout=10) as resp_track:
            xml_data = resp_track.read()
            
        root = ET.fromstring(xml_data)
        text_parts = [elem.text for elem in root.findall('.//text') if elem.text]
        return " ".join(text_parts)
    except Exception as e:
        st.error(f"Altyazı Çözümleme Hatası: {str(e)}")
        return None

# --- 🧠 AKILLI ÖZET MOTORU ---
def akilli_yerel_ozetleyici(metin):
    cumleler = re.split(r'(?<=[.!?])\s+', metin.strip())
    if len(cumleler) <= 5:
        return [f"📌 {c}" for c in cumleler if c.strip()]
    
    kelimeler = re.findall(r'\w+', metin.lower())
    durma_kelimeleri = {"ve", "veya", "ama", "fakat", "ile", "bir", "bu", "şu", "o", "da", "de", "için", "gibi", "çok", "en", "daha", "olan", "olarak"}
    frekanslar = {}
    for k in kelimeler:
        if k not in durma_kelimeleri and len(k) > 2:
            frekanslar[k] = frekanslar.get(k, 0) + 1
            
    cumle_puanlari = {}
    for idx, cumle in enumerate(cumleler):
        puan = 0
        for kelime in re.findall(r'\w+', cumle.lower()):
            if kelime in frekanslar:
                puan += frekanslar[kelime]
        cumle_puanlari[idx] = puan
        
    en_iyiler = sorted(cumle_puanlari, key=cumle_puanlari.get, reverse=True)[:5]
    en_iyiler.sort()
    
    emojiler = ["📌", "📊", "💡", "⚙️", "🎯"]
    sonuc_maddeleri = []
    for i, idx in enumerate(en_iyiler):
        temiz_cumle = cumleler[idx].strip()
        if len(temiz_cumle) > 150:
            temiz_cumle = temiz_cumle[:147] + "..."
        sonuc_maddeleri.append(f"{emojiler[i]} {temiz_cumle}")
        
    return sonuc_maddeleri

def pdf_rapor_uret(tarih, saat, orijinal_metin, ozet_maddeleri):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, title="AI Ozet Raporu")
    hikaye = []
    stiller = getSampleStyleSheet()
    
    baslik_stili = ParagraphStyle('RB', parent=stiller['Heading1'], fontSize=22, textColor=colors.HexColor('#1E3A8A'), spaceAfter=12)
    alt_baslik_stili = ParagraphStyle('RAB', parent=stiller['Normal'], fontSize=10, textColor=colors.gray, spaceAfter=20)
    madde_stili = ParagraphStyle('RM', parent=stiller['Normal'], fontSize=12, spaceAfter=10, leading=16)

    hikaye.append(Paragraph("📺 AI VİDEO & METİN ÖZETLEYİCİ RAPORU", baslik_stili))
    hikaye.append(Paragraph(f"Tarih: {tarih} | Saat: {saat}", alt_baslik_stili))
    hikaye.append(Spacer(1, 10))
    hikaye.append(Paragraph("<b>🤖 Çıkarılan 5 Kritik Madde:</b>", stiller['Heading2']))
    hikaye.append(Spacer(1, 5))
    
    for madde in ozet_maddeleri:
        hikaye.append(Paragraph(madde, madde_stili))
        
    hikaye.append(Spacer(1, 20))
    hikaye.append(Paragraph("<b>📝 Kaynak Metin (İlk Kısım):</b>", stiller['Heading2']))
    hikaye.append(Spacer(1, 5))
    hikaye.append(Paragraph(orijinal_metin[:500] + "...", stiller['Normal']))
    
    hikaye.append(Spacer(1, 30))
    hikaye.append(Paragraph("<font size=8 color=gray>Bu rapor bilgilendirme amaçlı üretilmiştir. AI yanıtları hata içerebilir.</font>", stiller['Normal']))
    
    doc.build(hikaye)
    buffer.seek(0)
    return buffer

def ozeti_ekrana_yazdir(tarih, saat, metin, ozet):
    st.divider()
    st.success(f"✅ İşlem Başarıyla Tamamlandı! ({tarih} - {saat})")
    
    pdf_dosyasi = pdf_rapor_uret(tarih, saat, metin, ozet)
    st.download_button(label="📥 Bu Özeti PDF Olarak İndir", data=pdf_dosyasi, file_name=f"ozet_{saat.replace(':','_')}.pdf", mime="application/pdf")
    
    st.subheader("📊 Analiz Edilen 5 Kritik Madde:")
    for madde in ozet: 
        st.write(madde)
        
    st.subheader("📝 Orijinal Kaynak:")
    st.caption(metin)

# --- 🚀 İŞLEME VE KAYDETME FONKSİYONLARI ---
def metni_ozetle_ve_kaydet(kaynak_metin):
    simdi = datetime.now()
    tarih = simdi.strftime("%d.%m.%Y")
    saat = simdi.strftime("%H:%M:%S")
    
    ozet_sonuc = akilli_yerel_ozetleyici(kaynak_metin)
    
    yeni_kayit = {
        "tarih": tarih,
        "saat": saat,
        "metin": kaynak_metin,
        "ozet": ozet_sonuc
    }
    veritabani_kaydet(yeni_kayit)
    ozeti_ekrana_yazdir(tarih, saat, kaynak_metin, ozet_sonuc)

# --- YAN MENÜ (SIDEBAR) ---
st.sidebar.title("📜 Özet Geçmişiniz")
gecmis_listesi = veritabani_yukle()
secilen_eski_ozet = None

if not gecmis_listesi:
    st.sidebar.info("Henüz geçmiş özetiniz bulunmuyor.")
else:
    for sira, g in enumerate(gecmis_listesi):
        buton_basligi = f"⏱️ {g['saat']} - {g['metin'][:25]}..."
        if st.sidebar.button(buton_basligi, key=f"gecmis_{sira}"):
            secilen_eski_ozet = g

st.sidebar.divider()
if st.sidebar.button("🗑️ Geçmişi Temizle"):
    if os.path.exists(VERITABANI_DOSYASI):
        os.remove(VERITABANI_DOSYASI)
        st.sidebar.success("Geçmiş silindi!")
        st.rerun()

# --- ANA SAYFA ---
st.title("📺 AI Akıllı Video & Metin Özetleyici SaaS")
st.write("Dış platformlara bağımlılığı olmayan, otomatik altyazı çözümlü kararlı sürüm.")
st.divider()

if secilen_eski_ozet:
    st.info("📂 **Geçmiş Özet Görüntüleniyor**")
    ozeti_ekrana_yazdir(secilen_eski_ozet['tarih'], secilen_eski_ozet['saat'], secilen_eski_ozet['metin'], secilen_eski_ozet['ozet'])
    if st.button("➕ Yeni Özet Oluşturma Ekranına Dön"): 
        st.rerun()

else:
    sekme1, sekme2 = st.tabs(["📺 YouTube Videosu Özetle", "📝 Uzun Metin/Yazı Özetle"])

    # TAB 1: YOUTUBE ÖZETLEME
    with sekme1:
        st.subheader("🚀 Sadece Linki Yapıştırın")
        video_linki = st.text_input("YouTube Linkini veya Video Kodunu Girin:", placeholder="Örn: https://youtube.com", key="yt_input")
        
        if st.button("Videoyu Analiz Et ve Özetle", key="yt_btn"):
            if not video_linki:
                st.warning("Lütfen bir link girin!")
            else:
                video_id = youtube_id_bul_kesin(video_linki)
                if not video_id:
                    st.error("❌ Geçersiz video kodu!")
                else:
                    st.info(f"🔍 Sistem: Video Kodu '{video_id}' başarıyla doğrulandı. Bağımsız altyazı motoru başlatılıyor...")
                    
                    PROJE_DIZINI = os.path.dirname(os.path.abspath(__file__))
                    CEREZ_YOLU = os.path.join(PROJE_DIZINI, "www.youtube.com_cookies.txt")
                    
                    with st.spinner("🤖 Güvenlik duvarları çerez entegrasyonuyla aşılıyor..."):
                        if not os.path.exists(CEREZ_YOLU):
                            st.error(f"⚠️ Kritik Hata: Klasörde 'www.youtube.com_cookies.txt' dosyası bulunamadı!")
