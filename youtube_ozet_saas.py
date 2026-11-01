import streamlit as st
import json
import os
import time
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
import io

# Web Sayfası Tasarımı
st.set_page_config(page_title="AI Özetleyici SaaS Pro", page_icon="🚀", layout="wide")

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

def yapay_zeka_ozet_motoru(metin):
    kelimeler = metin.split()
    if len(kelimeler) < 3:
        return ["Analiz için çok kısa bir metin girdiniz."]
    anahtar_1 = kelimeler[min(2, len(kelimeler)-1)].capitalize()
    anahtar_2 = kelimeler[min(len(kelimeler)//3, len(kelimeler)-1)] if len(kelimeler) > 3 else "İçerik"
    
    return [
        f"📌 **Ana Tema:** İçerikte temel olarak '{anahtar_1}' ve '{anahtar_2}' kavramları incelenmektedir.",
        f"📊 **Kritik Gözlem:** Yapılan analizlerde, süreçlerin işleyişi ve optimizasyon süreçleri ön plana çıkmaktadır.",
        f"💡 **Yapay Zeka Tavsiyesi:** Gelişim süreçlerinde bütçe tasarrufu ve kaynak yönetimi en önemli başarı kriteridir.",
        f"⚙️ **Uygulama Adımı:** Kısa vadeli geçici çözümler yerine, uzun vadeli Macro SaaS modellerine odaklanılmalıdır.",
        f"🎯 **Stratejik Sonuç:** Heddeflenen kitleye ulaşmak için adımların parçalara bölünerek yönetilmesi şarttır."
    ]

# --- 🛠️ YENİ: PDF RAPOR ÜRETME MOTORU ---
def pdf_rapor_uret(tarih, saat, orijinal_metin, ozet_maddeleri):
    """Kullanıcının indirmesi için bellek içinde şık bir PDF dosyası oluşturur."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, title="AI Ozet Raporu")
    hikaye = []
    
    # Rapor Stilleri
    stiller = getSampleStyleSheet()
    
    baslik_stili = ParagraphStyle(
        'RaporBaslik',
        parent=stiller['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#1E3A8A'),
        spaceAfter=12
    )
    
    alt_baslik_stili = ParagraphStyle(
        'RaporAltBaslik',
        parent=stiller['Normal'],
        fontSize=10,
        textColor=colors.gray,
        spaceAfter=20
    )
    
    madde_stili = ParagraphStyle(
        'RaporMadde',
        parent=stiller['Normal'],
        fontSize=12,
        spaceAfter=10,
        leading=16
    )

    # PDF İçeriğini Ekleme
    hikaye.append(Paragraph("📺 AI ÖZETLEYİCİ SAAS RAPORU", baslik_stili))
    hikaye.append(Paragraph(f"Tarih: {tarih} | Saat: {saat} | Rapor ID: #SR{int(time.time())}", alt_baslik_stili))
    hikaye.append(Spacer(1, 10))
    
    hikaye.append(Paragraph("<b>🤖 Yapay Zeka Özeti (5 Kritik Madde):</b>", stiller['Heading2']))
    hikaye.append(Spacer(1, 5))
    
    for madde in ozet_maddeleri:
        # Markdown yıldızlarını ve emojileri temizleyerek temiz metin basıyoruz
        temiz_madde = madde.replace("**", "").replace("📌", "-").replace("📊", "-").replace("💡", "-").replace("⚙️", "-").replace("🎯", "-")
        hikaye.append(Paragraph(temiz_madde, madde_stili))
        
    hikaye.append(Spacer(1, 20))
    hikaye.append(Paragraph("<b>📝 Orijinal Kaynak Metin (İlk Kısım):</b>", stiller['Heading2']))
    hikaye.append(Spacer(1, 5))
    hikaye.append(Paragraph(orijinal_metin[:500] + "...", stiller['Normal']))
    
    # Feragatname Notu (Sağlık/Klinik/Genel AI Uyarı Standardı)
    hikaye.append(Spacer(1, 30))
    hikaye.append(Paragraph("<font size=8 color=gray>Bu rapor bilgilendirme amaçlı yapay zeka tarafından üretilmiştir. AI yanıtları hata içerebilir.</font>", stiller['Normal']))
    
    doc.build(hikaye)
    buffer.seek(0)
    return buffer

# --- YAN MENÜ (SIDEBAR) - KULLANICI GEÇMİŞİ ---
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

# --- ANA SAYFA TASARIMI ---
st.title("🚀 AI Gelişmiş Özetleyici SaaS Panel")
st.write("Veritabanı ve PDF rapor desteğiyle, bütçesiz çalışan profesyonel MVP sürümü.")
st.divider()

# Durum 1: Geçmişten bir özete tıklandıysa
if secilen_eski_ozet:
    st.info(f"📂 **Geçmişten Görüntülenen Özet** ({secilen_eski_ozet['tarih']} - {secilen_eski_ozet['saat']})")
    
    # PDF İndirme Butonu Entegrasyonu
    pdf_dosyasi = pdf_rapor_uret(secilen_eski_ozet['tarih'], secilen_eski_ozet['saat'], secilen_eski_ozet['metin'], secilen_eski_ozet['ozet'])
    st.download_button(
        label="📥 Bu Özeti PDF Olarak İndir",
        data=pdf_dosyasi,
        file_name=f"ai_ozet_{secilen_eski_ozet['saat'].replace(':','_')}.pdf",
        mime="application/pdf"
    )
    
    st.subheader("🤖 Çıkarılan 5 Madde:")
    for madde in secilen_eski_ozet['ozet']:
        st.write(madde)
        
    st.subheader("📝 Orijinal Metin:")
    st.caption(secilen_eski_ozet['metin'])
    
    if st.button("➕ Yeni Özet Oluşturma Ekranına Dön"):
        st.rerun()

# Durum 2: Yeni Özet Oluşturma Ekranı
else:
    uzun_metin = st.text_area("Özetlenecek Metni Buraya Yapıştırın:", placeholder="Analiz edilecek yazıyı girin...", height=200)

    if st.button("Yapay Zeka ile Özetle ve Hafızaya Kaydet"):
        if not uzun_metin or len(uzun_metin.strip()) < 10:
            st.warning("Lütfen analiz edilebilmesi için yeterli uzunlukta bir metin girin!")
        else:
            with st.spinner("🤖 Yapay zeka veriyi işliyor..."):
                time.sleep(1)
            
            yapay_zeka_ozeti = yapay_zeka_ozet_motoru(uzun_metin)
            simdi = datetime.now()
            yeni_kayit = {
                "tarih": simdi.strftime("%d.%m.%Y"),
                "saat": simdi.strftime("%H:%M"),
                "metin": uzun_metin,
                "ozet": yapay_zeka_ozeti
            }
            veritabani_kaydet(yeni_kayit)
            st.rerun()
