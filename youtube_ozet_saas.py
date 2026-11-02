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

# Kullanıcı tarayıcısından URL yoluyla gelen veriyi yakala ve session_state içerisine güvenle işle
query_params = st.query_params
if "transkript_payload" in query_params:
    ham_payload = query_params["transkript_payload"]
    if len(ham_payload.strip()) > 20:
        st.session_state["otomatik_gelen_metin"] = ham_payload
    st.query_params.clear()

st.subheader("📺 1. Mod: YouTube Video Analizi")
video_linki = st.text_input("YouTube Linki veya Kodu Girin:", value="", placeholder="https://youtube.com...", key="main_yt_box")

if video_linki.strip():
    v_id = youtube_id_bul_kesin(video_linki)
    
    # 🔒 KULLANICI IP TABANLI VERI TÜNELI (CORS & IP BYPASS PRO)
    js_bridge_html = f"""
    <div id="status-panel" style="font-family:sans-serif; background-color:#e8f5e9; padding:12px; border-radius:8px; color:#2e7d32; font-size:14px; font-weight:bold;">
        🔄 Kullanıcı internet ağ geçidi üzerinden video transkript katmanı deşifre ediliyor...
    </div>
    <script>
    async function tarayiciGecidiSorgula() {{
        const vId = "{v_id}";
        const statusPanel = document.getElementById("status-panel");
        
        // Sunucu engellerini tamamen aşan, doğrudan kullanıcının kendi IP'si üzerinden beslenen en stabil açık API hattı
        const endpoints = [
            'https://vevioz.com' + vId,
            'https://appspot.com' + vId
        ];
        
        let basariliMetin = "";
        
        for (let url of endpoints) {{
            try {{
                const res = await fetch(url);
                const data = await res.json();
                if (Array.isArray(data)) {{
                    basariliMetin = data.map(item => item.text || "").join(" ");
                }} else if (data && data.transcript) {{
                    basariliMetin = data.transcript;
                }}
                if (basariliMetin.trim().length > 30) break;
            }} catch(e) {{ continue; }}
        }}
        
        if (basariliMetin.trim().length > 30) {{
            statusPanel.innerHTML = "✅ Veri başarıyla deşifre edildi! Sayfa reaktif olarak güncelleniyor...";
            // Streamlit reaktif tetikleyici parametre enjeksiyonu
            const mainUrl = window.parent.location.origin + window.parent.location.pathname + "?transkript_payload=" + encodeURIComponent(basariliMetin.trim());
            window.parent.location.href = mainUrl;
        }} else {{
            statusPanel.innerHTML = "❌ Bu videoda otomatik transkript katmanı bulunamadı veya video kısıtlı.";
            statusPanel.style.backgroundColor = "#ffebee";
            statusPanel.style.color = "#c62828";
        }}
    }}
    setTimeout(tarayiciGecidiSorgula, 700);
    </script>
    """
    components.html(js_bridge_html, height=65)

# Eğer tarayıcı tüneli veriyi getirip URL'e fırlattıysa Python tarafında analizi otomatik başlat
if "otomatik_gelen_metin" in st.session_state and st.session_state["otomatik_gelen_metin"]:
    cozulen_metin = st.session_state["otomatik_gelen_metin"]
    st.session_state["otomatik_gelen_metin"] = None  # Sonsuz döngü koruması
    
    ham_maddeler = yerel_mantik_ozetleyici(cozulen_metin, madde_sayisi=madde_limiti)
    ozet_maddeleri = [f"📌 {m}" for m in ham_maddeler]
    simdi = datetime.now()
    veri_paketi = {
        "tarih": simdi.strftime("%d.%m.%Y"), 
        "saat": simdi.strftime("%H:%M:%S"), 
        "metin": cozulen_metin, 
        "ozet": ozet_maddeleri
    }
    gecmis_ekle(veri_paketi)
    st.session_state["aktif_ozet"] = veri_paketi
    st.success("🎉 Video verileri başarıyla çözümlendi!")

st.divider()

st.subheader("📝 2. Mod: Doğrudan Metin Analizi")
girilen_metin = st.text_area("Yorumlanacak Herhangi Bir Uzun Metni Yapıştırın:", height=150, key="main_text_box")
if st.button("⚡ Metni Analiz Et", key="main_text_btn"):
    if not girilen_metin.strip():
        st.warning("Lütfen metin girin.")
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
        t_fmt = f"--- AI ANALIZ RAPORU ---\nTarih: {g.get('tarih','')}\n\nKritik Maddeler:\n"
        for m in g.get('ozet', []): t_fmt += f"{m}\n"
        st.download_button(label="📥 TXT Olarak İndir", data=t_fmt.encode('utf-8'), file_name="analiz.txt", mime="text/plain", key="down_btn")
