import streamlit as st
import json
import os
import time
from datetime import datetime
from youtube_transcript_api import YouTubeTranscriptApi
import re
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
import io

# Web Sayfası Tasarımı
st.set_page_config(page_title="AI Video & Metin Özetleyici SaaS", page_icon="📺", layout="wide")

# --- VERİTABANI (JSON) FONKSİYONLARI ---
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

# --- 🧠 %100 ÜCRETSİZ VE BAĞIMSIZ AKILLI ÖZET MOTORU ---
def akilli_yerel_ozetleyici(metin):
    """Metni cümlelere bölüp kelime frekans analiziyle en önemli 5 cümleyi seçer."""
    # Metni temizle ve cümlelere böl
    cumleler = re.split(r'(?<=[.!?])\s+', metin.strip())
    if len(cumleler) <= 5:
        return [f"📌 {c}" for c in cumleler if c.strip()]
    
    # Kelime frekanslarını (sıklıklarını) hesapla
    kelimeler = re.findall(r'\w+', metin.lower())
    durma_kelimeleri = {"ve", "veya", "ama", "fakat", "ile", "bir", "bu", "şu", "o", "da", "de", "için", "gibi", "çok", "en", "daha", "olan", "olarak"}
    frekanslar = {}
    for k in kelimeler:
        if k not in durma_kelimeleri and len(k) > 2:
            frekanslar[k] = frekanslar.get(k, 0) + 1
            
    # Cümleleri puanla
    cumle_puanlari = {}
    for idx, cumle in enumerate(cumleler):
        puan = 0
        for kelime in re.findall(r'\w+', cumle.lower()):
            if kelime in frekanslar:
                puan += frekanslar[kelime]
        cumle_puanlari[idx] = puan
        
    # En yüksek puanlı ilk 5 cümleyi orijinal sırasına göre seç
    en_iyiler = sorted(cumle_puanlari, key=cumle_puanlari.get, reverse=True)[:5]
    en_iyiler.sort()
    
    emojiler = ["📌", "📊", "💡", "⚙️", "🎯"]
    sonuc_maddeleri = []
    for i, idx in enumerate(en_iyiler):
        temiz_cumle = cumleler[idx].strip()
        # Çok uzun cümleleri kırp
        if len(temiz_cumle) > 150:
            temiz_cumle = temiz_cumle[:147] + "..."
        sonuc_maddeleri.append(f"{emojiler[i]} {temiz_cumle}")
        
    return sonuc_maddeleri

def pdf_rapor_uret(tarih, saat, orijinal_metin, ozet_maddeleri):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, title="AI Ozet Raporu")
    hikaye = []
    stiller = getSampleStyleSheet()
    
    baslik_stili = ParagraphStyle('RB', parent=stiller['Heading1'], fontSize=24, textColor=colors.HexColor('#1E3A8A'), spaceAfter=12)
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
    hikaye.append(Paragraph("<font size=8 color=gray>Bu rapor bilgilendirme amaçlı üretilmiştir. Yazılım metin madenciliği algoritması kullanılmıştır.</font>", stiller['Normal']))
    
    doc.build(buffer)
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
st.write("Dış platformlara bağımlılığı olmayan, ömür boyu ücretsiz ve kararlı sürüm.")
st.divider()

if secilen_eski_ozet:
    st.info("📂 **Geçmiş Özet Görüntüleniyor**")
    ozeti_ekrana_yazdir(secilen_eski_ozet['tarih'], secilen_eski_ozet['saat'], secilen_eski_ozet['metin'], secilen_eski_ozet['ozet'])
    if st.button("➕ Yeni Özet Oluşturma Ekranına Dön"): st.rerun()

else:
    sekme1, sekme2 = st.tabs(["📺 YouTube Videosu Özetle", "📝 Uzun Metin/Yazı Özetle"])

    # TAB 1: YOUTUBE ÖZETLEME
    with sekme1:
        video_linki = st.text_input("YouTube Linki veya 11 Haneli Video Kodu Girin:", placeholder="Örn: mJYxSed0D_I", key="yt_input")
        
        if st.button("Videoyu Analiz Et ve Özetle", key="yt_btn"):
            if not video_linki:
                st.warning("Lütfen bir giriş yapın!")
            else:
                video_id = youtube_id_bul_kesin(video_linki)
                if not video_id:
                    st.error("❌ Geçersiz video kodu!")
                else:
                    st.info(f"🔍 Sistem: Video Kodu '{video_id}' başarıyla yakalandı.")
                    
                    with st.spinner("İçerik analiz ediliyor..."):
                        try:
                            konusma_verisi = YouTubeTranscriptApi.get_transcript(video_id, languages=['tr', 'en'])
                            metin_to_process = " ".join([parca['text'] for parca in konusma_verisi])
                            yapay_zeka_ozeti = akilli_yerel_ozetleyici(metin_to_process)
                        except:
                            st.error("⚠️ Bu videonun altyazı korumasını otomatik aşamadık.")
                            st.info("💡 Lütfen videonun altındaki altyazıları kopyalayıp yan taraftaki 'Uzun Metin/Yazı Özetle' sekmesine yapıştırın. Sistemimiz onu kusursuzca özetleyecektir!")
                            metin_to_process = ""
                    
                    if metin_to_process:
                        simdi = datetime.now()
                        t_sn = simdi.strftime("%d.%m.%Y")
                        s_sn = simdi.strftime("%H:%M")
                        veritabani_kaydet({"tarih": t_sn, "saat": s_sn, "metin": metin_to_process, "ozet": yapay_zeka_ozeti})
                        ozeti_ekrana_yazdir(t_sn, s_sn, metin_to_process, yapay_zeka_ozeti)

    # TAB 2: METİN ÖZETLEME
    with sekme2:
        uzun_metin = st.text_area("Özetlenecek Metni (veya kopyaladığınız altyazıları) Buraya Yapıştırın:", placeholder="Yazınızı buraya girin...", height=150, key="txt_input")
        if st.button("Metni Analiz Et ve Özetle", key="txt_btn"):
            if not uzun_metin or len(uzun_metin.strip()) < 10:
                st.warning("Lütfen metin girin!")
            else:
                with st.spinner("Metin analiz ediliyor..."):
                    yapay_zeka_ozeti = akilli_yerel_ozetleyici(uzun_metin)
                
                simdi = datetime.now()
                t_sn = simdi.strftime("%d.%m.%Y")
                s_sn = simdi.strftime("%H:%M")
                veritabani_kaydet({"tarih": t_sn, "saat": s_sn, "metin": uzun_metin, "ozet": yapay_zeka_ozeti})
                ozeti_ekrana_yazdir(t_sn, s_sn, uzun_metin, yapay_zeka_ozeti)
