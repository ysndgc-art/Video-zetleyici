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
st.write("Gelişmiş İstatistik Paneli ve Kesintisiz Çözüm Altyapısı")
st.divider()

madde_limiti = st.slider("Çıkarılacak Kritik Madde Sayısı:", min_value=3, max_value=15, value=5, step=1)

st.subheader("📺 1. Mod: YouTube Video Analizi")
video_linki = st.text_input("YouTube Linki veya Kodu Girin:", value="", placeholder="https://youtube.com...", key="main_yt_box")

if video_linki.strip():
    v_id = youtube_id_bul_kesin(video_linki)
    
    # KULLANICI TARAYICISI ÜZERİNDEN DOĞRUDAN ENGELSİZ BAĞLANTI KÖPRÜSÜ
    js_bridge_html = f"""
    <div id="status-box" style="font-family:sans-serif; background-color:#f0f2f6; padding:12px; border-radius:8px; color:#333; font-size:14px;">
        🔄 Kullanıcı yerel ağ geçidi üzerinden video döküm verileri işleniyor...
    </div>
    <script>
    async function tarayiciUzerindenCek() {{
        const vId = "{v_id}";
        const statusBox = document.getElementById("status-box");
        try {{
            // Doğrudan kullanıcının tarayıcısından istek atıldığı için bulut IP engeli tamamen aşılır
            const response = await fetch('https://allorigins.win' + encodeURIComponent('https://youtubetranscript.com' + vId));
            const data = await response.json();
            
            if (data.contents && data.contents.includes('<text')) {{
                const parser = new DOMParser();
                const xmlDoc = parser.parseFromString(data.contents, "text/xml");
                const lines = xmlDoc.getElementsByTagName("text");
                let metinHavuzu = "";
                for (let i = 0; i < lines.length; i++) {{
                    metinHavuzu += lines[i].textContent + " ";
                }}
                
                // Streamlit form alanını arka planda güvenle besle
                const textarea = window.parent.document.querySelector('textarea[aria-label="Yorumlanacak Herhangi Bir Uzun Metni Yapıştırın:"]');
                if (textarea) {{
                    textarea.value = metinHavuzu.trim();
                    textarea.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    statusBox.innerHTML = "✅ Video verisi başarıyla yakalandı! Aşağıdaki panelden <b>'Metni Analiz Et'</b> butonuna tıklayarak raporunuzu üretebilirsiniz.";
                    statusBox.style.backgroundColor = "#e8f5e9";
                    statusBox.style.color = "#2e7d32";
                }}
            }} else {{
                statusBox.innerHTML = "⚠️ Bu video için otomatik/manuel üretilmiş transkript katmanı bulunamadı veya video korumalı.";
                statusBox.style.backgroundColor = "#ffebee";
                statusBox.style.color = "#c62828";
            }}
        }} catch(e) {{
            statusBox.innerHTML = "❌ Güvenli veri tünelinde tarayıcı CORS kısıtlaması algılandı.";
            statusBox.style.backgroundColor = "#ffebee";
            statusBox.style.color = "#c62828";
        }}
    }}
    setTimeout(tarayiciUzerindenCek, 600);
    </script>
    """
    components.html(js_bridge_html, height=75)

st.divider()

st.subheader("📝 2. Mod: Doğrudan Metin Analizi")
girilen_metin = st.text_area("Yorumlanacak Herhangi Bir Uzun Metni Yapıştırın:", height=150, key="main_text_box")

if st.button("⚡ Metni Analiz Et", key="main_text_btn"):
    if not girilen_metin.strip():
        st.warning("Lütfen analiz edilecek bir içeriği buraya yapıştırın veya yukarıya geçerli bir link girin.")
    else:
        ham_maddeler = yerel_mantik_ozetleyici(girilen_metin, madde_sayisi=madde_limiti)
        ozet_maddeleri = [f"💡 {m}" for m in ham_maddeler]
        simdi = datetime.now()
        veri_paketi = {"tarih": simdi.strftime("%d.%m.%Y"), "saat": simdi.strftime("%H:%M:%S"), "metin": girilen_metin, "ozet": ozet_maddeleri}
        gecmis_ekle(veri_paketi)
        st.session_state["aktif_ozet"] = veri_paketi
        st.rerun()

# --- SONUÇ ALANI ---
if "aktif_ozet" in st.session_state and st.session_state["aktif_ozet"] is not None:
    st.divider()
    st.info("📂 **Analiz Sonucu**")
    g = st.session_state["aktif_ozet"]
    if isinstance(g, dict) and "ozet" in g:
        for m in g.get('ozet', []):
            st.write(m)
        st.divider()
        txt_cikisi = f"--- AI ANALIZ RAPORU ---\nTarih: {g.get('tarih','')}\n\nKritik Maddeler:\n"
        for m in g.get('ozet', []): txt_cikisi += f"{m}\n"
        st.download_button(label="📥 TXT Olarak İndir", data=txt_cikisi.encode('utf-8'), file_name="analiz.txt", mime="text/plain", key="down_btn")
