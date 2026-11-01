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
import yt_dlp

# Sayfa Yapılandırması
st.set_page_config(page_title="AI Video & Metin Özetleyici SaaS", page_icon="📺", layout="wide")

if "video_id" not in st.session_state:
    st.session_state.video_id = None
if "islem_basladi" not in st.session_state:
    st.session_state.islem_basladi = False

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
    
    doc.build(hikaye)
    buffer.seek(0)
    return buffer

def ozeti_ekrana_yazdir(tarih, saat, metin, ozet):
    st.divider()
    st.success(f"✅ İşlem Başarıyla Tamamlandı! ({tarih} - {saat})")
    pdf_dosyasi = pdf_rapor_uret(tarih, saat, metin, ozet)
    st.download_button(label="📥 Bu Özeti PDF Olarak İndir", data=pdf_dosyasi, file_name=f"ozet_{saat.replace(':','_')}.pdf", mime="application/pdf")
    st.subheader("📊 Analiz Edilen 5 Kritik Madde:")
    for m in ozet: st.write(m)
    st.subheader("📝 Orijinal Kaynak:")
    st.caption(metin)

def metni_ozetle_ve_kaydet(kaynak_metin):
    simdi = datetime.now()
    tarih = simdi.strftime("%d.%m.%Y")
    saat = simdi.strftime("%H:%M:%S")
    ozet_sonuc = akilli_yerel_ozetleyici(kaynak_metin)
    yeni_kayit = {"tarih": tarih, "saat": saat, "metin": kaynak_metin, "ozet": ozet_sonuc}
    veritabani_kaydet(yeni_kayit)
    ozeti_ekrana_yazdir(tarih, saat, kaynak_metin, ozet_sonuc)

def ytdlp_altyazi_cek(video_id, cerez_yolu):
    ydl_opts = {
        'writesubtitles': True,
        'writeautomaticsub': True,
        'subtitleslangs': ['tr', 'en', 'auto'],
        'skip_download': True,
        'cookiefile': cerez_yolu,
        'outtmpl': f"sub_{video_id}",
        'quiet': True,
        'no_warnings': True
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([f"https://youtube.com{video_id}"])
        altyazi_metni = ""
        bulunan_dosya = None
        for dosya in os.listdir("."):
            if dosya.startswith(f"sub_{video_id}") and dosya.endswith(".vtt"):
                bulunan_dosya = dosya
                break
        if bulunan_dosya and os.path.exists(bulunan_dosya):
            with open(bulunan_dosya, "r", encoding="utf-8") as f:
                vtt_content = f.read()
            lines = vtt_content.split("\n")
            temiz_satirlar = []
            for line in lines:
                if "-->" not in line and line.strip() and not line.strip().isdigit() and "WEBVTT" not in line and "Kind:" not in line and "Language:" not in line:
                    clean_line = re.sub(r'<[^>]*>', '', line).strip()
                    if clean_line and (not temiz_satirlar or temiz_satirlar[-1] != clean_line):
                        temiz_satirlar.append(clean_line)
            altyazi_metni = " ".join(temiz_satirlar)
            try: os.remove(bulunan_dosya)
            except: pass
            return altyazi_metni
    except Exception as e:
        st.error(f"Sistem Hatası: {str(e)}")
    return None

# Yan Menü Gecmiş Yönetimi
st.sidebar.title("📜 Özet Geçmişiniz")
gecmis_listesi = veritabani_yukle()
secilen_eski_ozet = None

if not gecmis_listesi:
    st.sidebar.info("Henüz geçmiş özetiniz bulunmuyor.")
else:
    for sira, g in enumerate(gecmis_listesi):
        if st.sidebar.button(f"⏱️ {g['saat']} - {g['metin'][:20]}...", key=f"g_{sira}"):
            secilen_eski_ozet = g

st.sidebar.divider()
if st.sidebar.button("🗑️ Geçmişi Temizle"):
    if os.path.exists(VERITABANI_DOSYASI):
        os.remove(VERITABANI_DOSYASI)
        st.sidebar.success("Geçmiş silindi!")
        st.rerun()

# Ana Sayfa Tasarımı
st.title("📺 AI Akıllı Video & Metin Özetleyici SaaS")
st.write("Kararlı ve hatasız çalışan düzleştirilmiş yeni sürüm.")
st.divider()

if secilen_eski_ozet:
    st.info("📂 **Geçmiş Özet Görüntüleniyor**")
    ozeti_ekrana_yazdir(secilen_eski_ozet['tarih'], secilen_eski_ozet['saat'], secilen_eski_ozet['metin'], secilen_eski_ozet['ozet'])
    if st.button("➕ Yeni Özet Ekranına Dön"):
        st.rerun()
else:
    mod_secimi = st.radio("Lütfen Özetleme Modu Seçin:", ["📺 YouTube Videosu Özetle", "📝 Uzun Metin Özetle"], horizontal=True)
    
    if mod_secimi == "📺 YouTube Videosu Özetle":
        st.subheader("🚀 Sadece Linki Yapıştırın")
        video_linki = st.text_input("YouTube Linkini veya Video Kodunu Girin:", placeholder="Örn: kqtD5dpn9C8")
        if st.button("Videoyu Analiz Et ve Özetle"):
            v_id = youtube_id_bul_kesin(video_linki)
            if not video_linki:
                st.warning("Lütfen bir link girin!")
            elif not v_id:
                st.error("❌ Geçersiz video kodu!")
            else:
                st.session_state.video_id = v_id
                st.session_state.islem_basladi = True
                st.rerun()
                
        if st.session_state.islem_basladi and st.session_state.video_id:
            st.info(f"🔍 Sistem: Video Kodu '{st.session_state.video_id}' doğrulandı.")
            PROJE_DIZINI = os.path.dirname(os.path.abspath(__file__))
            CEREZ_YOLU = os.path.join(PROJE_DIZINI, "www.youtube.com_cookies.txt")
            
            metin_to_process = ""
            with st.spinner("🤖 Altyazılar güvenli motorla çekiliyor..."):
                if not os.path.exists(CEREZ_YOLU):
                    st.error("⚠️ Kritik Hata: 'www.youtube.com_cookies.txt' dosyası bulunamadı!")
                else:
                    metin_to_process = ytdlp_altyazi_cek(st.session_state.video_id, CEREZ_YOLU)
            
            st.session_state.islem_basladi = False
            st.session_state.video_id = None
            
            if metin_to_process:
                metni_ozetle_ve_kaydet(metin_to_process)
            else:
                st.error("❌ Altyazı indirilemedi veya video korumalı.")
                
    if mod_secimi == "📝 Uzun Metin Özetle":
        st.subheader("📝 Metni Buraya Yapıştırın")
        girilen_metin = st.text_area("Özetlenecek Metin:", placeholder="Yazınızı buraya ekleyin...", height=250)
        if st.button("Metni Analiz Et ve Özetle"):
            if not girilen_metin.strip():
                st.warning("Lütfen boş bir metin bırakmayın!")
            else:
                with st.spinner("🤖 Metin analiz ediliyor..."):
                    metni_ozetle_ve_kaydet(girilen_metin)
