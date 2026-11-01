import streamlit as st
import json
import os
import re
import requests
import time

st.set_page_config(page_title="AI Video Özetleyici SaaS", page_icon="📺", layout="wide")

VERITABANI_DOSYASI = "ozet_gecmisi.json"
HF_API_TOKEN = st.sidebar.text_input("🤗 Hugging Face Access Token:", type="password")

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

def yapay_zeka_ozetle(altyazi_metni):
    if not HF_API_TOKEN:
        return "⚠️ Lütfen sol menüden Hugging Face Access Token girişini yapın!"
    API_URL = "https://huggingface.co"
    headers = {"Authorization": f"Bearer {HF_API_TOKEN.strip()}"}
    prompt = f"Sana verilen YouTube video altyazısını tamamen TÜRKÇE olarak özetle:\n\n{altyazi_metni[:4000]}"
    payload = {"inputs": prompt, "parameters": {"max_new_tokens": 500, "temperature": 0.3}}
    try:
        response = requests.post(API_URL, headers=headers, json=payload, timeout=30)
        res_json = response.json()
        if isinstance(res_json, list) and len(res_json) > 0:
            return res_json[0].get("generated_text", "").replace(prompt, "").strip()
        elif isinstance(res_json, dict) and "generated_text" in res_json:
            return res_json["generated_text"].replace(prompt, "").strip()
        return f"API Yanıt Hatası: {str(res_json)}"
    except Exception as e:
        return f"Bağlantı Hatası: {str(e)}"

st.sidebar.title("📜 Özet Geçmişiniz")
gecmis = veritabani_yukle()
for g in gecmis[:10]:
    st.sidebar.write(f"⏱️ {g.get('ozet','')[:20]}...")

st.title("📺 AI Akıllı Video & Metin Özetleyici SaaS")
st.write("Sıfır Önbellek Kilitlenmeli Stabil Sürüm")

girilen_metin = st.text_area("Özetlenecek Metni veya Altyazıyı Girin:", height=250)
if st.button("Yapay Zekayla Özetle"):
    if not girilen_metin.strip():
        st.warning("Lütfen boş metin bırakmayın.")
    else:
        with st.spinner("🤖 Yapay zeka analiz ediyor..."):
            sonuc = yapay_zeka_ozetle(girilen_metin)
        st.subheader("📊 Yapay Zeka Çıktısı:")
        st.info(sonuc)
