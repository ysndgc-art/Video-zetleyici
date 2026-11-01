import streamlit as st
import json
import os
import re
import requests
import time
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

# --- 🤖 HUGGING FACE GÜVENLİ YAPAY ZEKA MOTORU ---
def yapay_zeka_ozetle(altyazi_metni):
    if not HF_API_TOKEN:
        return "⚠️ Lütfen sol menüden ücretsiz Hugging Face Access Token girişini yapın!"
        
    # Sunucu yoğunluğuna karşı en kararlı çalışan alternatif Llama-3 API uç noktası
    API_URL = "https://huggingface.co"
    headers = {"Authorization": f"Bearer {HF_API_TOKEN.strip()}"}
    
    prompt = f"<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n" \
             f"Sen profesyonel bir içerik analistisin. Sana verilen YouTube video altyazısını inceleyip " \
             f"tamamen TÜRKÇE, akıcı, mantıklı cümlelerle analiz etmelisin. Yanıtını şu şablona sadık kalarak oluştur:\n\n" \
             f"📌 GENEL ÖZET: (Videonun ana fikrini anlatan 2-3 cümle)\n\n" \
             f"💡 ÖNEMLİ ÇIKARIMLAR:\n- (Kritik nokta 1)\n- (Kritik nokta 2)\n- (Kritik nokta 3)\n\n" \
             f"🎯 SONUÇ VE DEĞERLENDİRME: (Kapanış cümlesi)<|eot_id|>" \
             f"<|start_header_id|>user<|end_header_id|>\n" \
             f"Lütfen şu video içeriğini yukarıdaki şablona göre analiz et:\n{altyazi_metni[:4000]}<|eot_id|>" \
             f"<|start_header_id|>assistant<|end_header_id|>\n"

    payload = {
        "inputs": prompt,
        "parameters": {"max_new_tokens": 800, "temperature": 0.3, "return_full_text": False}
    }
    
    try:
        response = requests.post(API_URL, headers=headers, json=payload, timeout=30)
        
        # HTTP Durum kontrolü (Boş veya hatalı HTML dönüşlerini yakalamak için)
        if response.status_code == 503:
            return "⏳ Yapay zeka modeli şu an Hugging Face sunucularına yükleniyor/uyanıyor. Lütfen 15-20 saniye sonra tekrar deneyin."
        if response.status_code == 401:
            return "❌ Geçersiz API Token! Lütfen sol menüdeki Hugging Face Access Token'ı doğru girdiğinizden emin olun."
            
        # JSON ayrıştırma hatasını (Expecting value) yakalayan güvenli blok
        try:
            res_json = response.json()
        except ValueError:
            return f"❌ API boş yanıt döndürdü (HTTP {response.status_code}). Hugging Face sunucuları şu an yoğun olabilir, lütfen butona tekrar basın."
        
        # Model yüklenme aşamasındaysa bekletip otomatik tekrar deneme
        if isinstance(res_json, dict) and "error" in res_json and "loading" in res_json["error"]:
            st.warning("⏳ Model sunucuda hazırlanıyor, otomatik olarak 8 saniye bekleniyor...")
            time.sleep(8)
            response = requests.post(API_URL, headers=headers, json=payload, timeout=30)
            try:
                res_json = response.json()
            except ValueError:
                return "❌ Model uyandırma aşamasında API bağlantısı koptu. Lütfen tekrar deneyin."
            
        if isinstance(res_json, list) and len(res_json) > 0:
            text_field = res_json[0].get("generated_text", "")
            return text_field.replace(prompt, "").strip()
        elif isinstance(res_json, dict) and "generated_text" in res_json:
            return res_json["generated_text"].replace(prompt, "").strip()
        elif isinstance(res_json, dict) and "error" in res_json:
            return f"⚠️ Hugging Face API Hatası: {res_json['error']}"
        else:
            return "Özet üretilemedi. Sunucu yanıt biçimi tanınamadı."
            
    except requests.exceptions.Timeout:
        return "⏱️ Yapay zeka isteği zaman aşımına uğradı. Sunucu şu an çok yoğun olabilir."
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
st.write("Güvenli API Hata Yönetimli Sürüm")

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
                
                if "❌" in ai_ozet or "⚠️" in ai_ozet or "⏳" in ai_ozet:
                    st.error(ai_ozet)
                else:
                    simdi = datetime.now()
                    tarih_str = simdi.strftime("%d.%m.%Y")
                    saat_str = simdi.strftime("%H:%M:%S")
                    
                    veritabani_kaydet({"tarih": tarih_str, "saat": saat_str, "metin": metin, "ozet": ai_ozet})
                    st.success("✅ Analiz Tamamlandı!")
                    
                    pdf_dosya = pdf_rapor_uret(tarih_str, saat_str, ai_ozet)
                    st.download_button(label="📥 Yapay Zeka Özetini PDF Olarak İndir", data=pdf_dosya, file_name=f"AI_Ozet_{v_id}.pdf", mime="application/pdf")
                    
                    st.subheader("📊 Yapay Zeka Mantıksal Analiz Raporu:")
                    st.info(ai_ozet)
            else:
