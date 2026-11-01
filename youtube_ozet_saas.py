import streamlit as st
import json
import os
import re
import requests
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
import io
import yt_dlp

# --- SAYFA YAPILANDIRMASI ---
st.set_page_config(page_title="AI Video Özetleyici SaaS", page_icon="📺", layout="wide")

VERITABANI_DOSYASI = "ozet_gecmisi.json"

# --- HUGGING FACE APİ AYARI ---
# Yukarıda aldığınız hf_... kodunu buraya yapıştırabilirsiniz veya boş bırakıp arayüzden girebilirsiniz.
HF_API_TOKEN = st.sidebar.text_input("🤗 Hugging Face Access Token:", type="password", help="huggingface.co adresinden aldığınız ücretsiz Read tokenını buraya girin.")

def veritabani_yukle():
    if os.path.exists(VERITABANI_DOSYASI):
        with open(VERITABANI_DOSYASI, "r", encoding="utf-8") as f:
            try: return json.load(f)
            except: return []
    return []

def veritabani_kaydet(yeni_ozet):
    gecmis = veritabani_yukle()
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

# --- 🤖 HUGGING FACE ÜCRETSİZ YAPAY ZEKA MOTORU ---
def yapay_zeka_ozetle(altyazi_metni):
    if not HF_API_TOKEN:
        return "⚠️ Lütfen sol menüden ücretsiz Hugging Face Access Token girişini yapın!"
        
    # Dünyanın en iyi açık kaynaklı modellerinden Meta Llama 3 API uç noktası
    API_URL = "https://huggingface.co"
    headers = {"Authorization": f"Bearer {HF_API_TOKEN}"}
    
    # Yapay zekaya Türkçe karakter sınırlarına uygun, yapılandırılmış rol emri (Prompt) veriyoruz
    prompt = f"<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n" \
             f"Sen profesyonel bir içerik analistisin. Sana verilen YouTube video altyazısını inceleyip " \
             f"tamamen TÜRKÇE, akıcı, mantıklı cümlelerle analiz etmelisin. Yanıtını şu şablona sadık kalarak oluştur:\n" \
             f"📌 GENEL ÖZET: (Videonun ana fikrini anlatan 2-3 cümle)\n" \
             f"💡 ÖNEMLİ ÇIKARIMLAR:\n- (Kritik nokta 1)\n- (Kritik nokta 2)\n- (Kritik nokta 3)\n" \
             f"🎯 SONUÇ VE DEĞERLENDİRME: (Kapanış cümlesi)<|eot_id|>" \
             f"<|start_header_id|>user<|end_header_id|>\n" \
             f"Lütfen şu video içeriğini yukarıdaki şablona göre analiz et:\n{altyazi_metni[:4000]}<|eot_id|>" \
             f"<|start_header_id|>assistant<|end_header_id|>\n"

    payload = {
        "inputs": prompt,
        "parameters": {"max_new_tokens": 800, "temperature": 0.3, "return_full_text": False}
    }
    
    try:
        response = requests.post(API_URL, headers=headers, json=payload)
        res_json = response.json()
        
        # API bazen model yüklenirken bekletebilir, otomatik sarmalayıcı kuruyoruz
        if "error" in res_json and "loading" in res_json["error"]:
            time.sleep(5) # Modelin uyanması için kısa bir bekleme süresi
            response = requests.post(API_URL, headers=headers, json=payload)
            res_json = response.json()
            
        if isinstance(res_json, list) and len(res_json) > 0:
            return res_json[0].get("generated_text", "Özet üretilemedi.").strip()
        elif isinstance(res_json, dict) and "generated_text" in res_json:
            return res_json["generated_text"].strip()
        else:
            return f"Yapay zeka motoru şu an meşgul veya hata döndürdü: {str(res_json)}"
    except Exception as e:
        return f"Yapay Zeka API Bağlantı Hatası: {str(e)}"

# --- 📄 PDF RAPOR MOTORU ---
def pdf_rapor_uret(tarih, saat, ozet_metni):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, title="AI Video Analiz Raporu")
    hikaye = []
    stiller = getSampleStyleSheet()
    
    baslik_stili = ParagraphStyle('RB', parent=stiller['Heading1'], fontSize=20, textColor=colors.HexColor('#1E3A8A'), spaceAfter=12)
    alt_baslik_stili = ParagraphStyle('RAB', parent=stiller['Normal'], fontSize=10, textColor=colors.gray, spaceAfter=20)
    metin_stili = ParagraphStyle('RM', parent=stiller['Normal'], fontSize=11, spaceAfter=8, leading=16)

    hikaye.append(Paragraph("📺 AI VİDEO ANALİZ VE ÖZET RAPORU", baslik_stili))
    hikaye.append(Paragraph(f"Tarih: {tarih} | Saat: {saat}", alt_baslik_stili))
    hikaye.append(Spacer(1, 10))
    
    # Satır satır PDF'e ekleme
    for satir in ozet_metni.split("\n"):
        if satir.strip():
            hikaye.append(Paragraph(satir, metin_stili))
    
    doc.build(hikaye)
    buffer.seek(0)
    return buffer

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
            return " ".join(temiz_satirlar)
    except Exception as e:
        st.error(f"Altyazı Motor Hatası: {str(e)}")
    return None

# --- SIDEBAR GEÇMİŞ ---
st.sidebar.title("📜 Özet Geçmişiniz")
gecmis = veritabani_yukle()
for g in gecmis[:10]:
    st.sidebar.write(f"⏱️ {g.get('saat','')} - {g.get('ozet','')[:25]}...")

# --- ANA SAYFA ---
st.title("📺 AI Akıllı Video & Metin Özetleyici SaaS")
st.write("Meta Llama 3 Yapay Zeka Entegrasyonlu Yeni Sürüm")

mod = st.radio("Mod Seçin:", ["📺 YouTube Videosu", "📝 Uzun Metin"], horizontal=True)

if mod == "📺 YouTube Videosu":
    video_linki = st.text_input("YouTube Linki veya Kodu:", value="1OkydHdhABQ")
    if st.button("Videoyu Yapay Zekayla Analiz Et"):
        if not HF_API_TOKEN:
            st.warning("⚠️ Lütfen önce sol menüye Hugging Face Token'ınızı girin!")
        else:
            v_id = youtube_id_bul_kesin(video_linki)
            PROJE_DIZINI = os.path.dirname(os.path.abspath(__file__))
            CEREZ_YOLU = os.path.join(PROJE_DIZINI, "www.youtube.com_cookies.txt")
            
            with st.spinner("📥 1. Adım: Altyazılar YouTube'dan çekiliyor..."):
                metin = ytdlp_altyazi_cek(v_id, CEREZ_YOLU)
                
            if metin:
                with st.spinner("🤖 2. Adım: Yapay zeka cümleleri mantıksal süzgeçten geçirip özetliyor..."):
                    ai_ozet = yapay_zeka_ozetle(metin)
                
                simdi = datetime.now()
                tarih_str = simdi.strftime("%d.%m.%Y")
                saat_str = simdi.strftime("%H:%M:%S")
                
                # Veritabanına kaydet
                veritabani_kaydet({"tarih": tarih_str, "saat": saat_str, "metin": metin, "ozet": ai_ozet})
                
                st.success("✅ Analiz Tamamlandı!")
                
                # PDF Rapor İndirme Butonu
                pdf_dosya = pdf_rapor_uret(tarih_str, saat_str, ai_ozet)
                st.download_button(label="📥 Yapay Zeka Özetini PDF Olarak İndir", data=pdf_dosya, file_name=f"AI_Ozet_{v_id}.pdf", mime="application/pdf")
                
                st.subheader("📊 Yapay Zeka Mantıksal Analiz Raporu:")
                st.info(ai_ozet)
            else:
                st.error("Altyazı indirilemedi. Videoda altyazı açık olduğundan emin olun.")

if mod == "📝 Uzun Metin":
    girilen_metin = st.text_area("Özetlenecek Metni Girin:", height=200)
    if st.button("Metni Yapay Zekayla Özetle"):
        if not HF_API_TOKEN:
            st.warning("⚠️ Lütfen önce sol menüye Hugging Face Token'ınızı girin!")
        elif not girilen_metin.strip():
            st.warning("Metin alanı boş bırakılamaz.")
        else:
            with st.spinner("🤖 Yapay zeka metni analiz ediyor..."):
                ai_ozet = yapay_zeka_ozetle(girilen_metin)
            
            st.success("✅ İşlem Başarılı!")
            st.subheader("📊 Yapay Zeka Analizi:")
            st.info(ai_ozet)
