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
    
    # 🔒 RESMİ YOUTUBE OYNATICI API KÖPRÜSÜ (CORS & IP BYPASS)
    js_bridge_html = f"""
    <div id="status-box" style="font-family:sans-serif; background-color:#e8f5e9; padding:12px; border-radius:8px; color:#2e7d32; font-size:14px; margin-bottom:10px; font-weight:bold;">
        ✅ Resmi YouTube API Modülü Hazırlandı. Video verileri deşifre ediliyor...
    </div>
    <!-- Gizli Resmi Oynatıcı DOM Elemanı -->
    <div id="yt-official-player" style="position:absolute; width:1px; height:1px; opacity:0.01; pointer-events:none;"></div>

    <script>
    // YouTube Iframe API asenkron yükleyici hattı
    if (!window.YT) {{
        var tag = document.createElement('script');
        tag.src = "https://youtube.com";
        var firstScriptTag = document.getElementsByTagName('script')[0];
        firstScriptTag.parentNode.insertBefore(tag, firstScriptTag);
    }}

    var player;
    window.onYouTubeIframeAPIReady = function() {{
        player = new YT.Player('yt-official-player', {{
            videoId: '{v_id}',
            playerVars: {{
                'cc_load_policy': 1,
                'cc_lang_pref': 'tr'
            }},
            events: {{
                'onReady': onPlayerReady
            }}
        }});
    }};

    function onPlayerReady(event) {{
        const statusBox = document.getElementById("status-box");
        const videoId = "{v_id}";
        
        // Resmi timedtext API'sine tarayıcı kimliği üzerinden direkt yasal çağrı yapılması
        const targetUrl = 'https://youtube.com' + videoId + '&lang=tr&fmt=srv1';
        
        fetch(targetUrl)
        .then(res => res.text())
        .then(xmlText => {{
            if (xmlText && xmlText.includes('<text')) {{
                var parser = new DOMParser();
                var xmlDoc = parser.parseFromString(xmlText, "text/xml");
                var lines = xmlDoc.getElementsByTagName("text");
                var tamMetin = "";
                for (var i = 0; i < lines.length; i++) {{
                    tamMetin += lines[i].textContent + " ";
                }}
                
                // Streamlit form elementine asenkron tünelleme
                const textarea = window.parent.document.querySelector('textarea[aria-label="Yorumlanacak Herhangi Bir Uzun Metni Yapıştırın:"]');
                if (textarea) {{
                    textarea.value = tamMetin.trim();
                    textarea.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    statusBox.innerHTML = "🎉 Video veri katmanı başarıyla deşifre edildi ve kutuya aktarıldı! 'Metni Analiz Et' butonuna basabilirsiniz.";
                    statusBox.style.backgroundColor = "#e8f5e9";
                    statusBox.style.color = "#2e7d32";
                }}
            }} else {{
                // Alternatif dil taraması (İngilizce vb.)
                fetch('https://youtube.com' + videoId + '&fmt=srv1')
                .then(r => r.text())
                .then(altXml => {{
                    if(altXml && altXml.includes('<text')) {{
                        var parser = new DOMParser();
                        var xmlDoc = parser.parseFromString(altXml, "text/xml");
                        var lines = xmlDoc.getElementsByTagName("text");
                        var tamMetin = "";
                        for (var i = 0; i < lines.length; i++) {{
                            tamMetin += lines[i].textContent + " ";
                        }}
                        const textarea = window.parent.document.querySelector('textarea[aria-label="Yorumlanacak Herhangi Bir Uzun Metni Yapıştırın:"]');
                        if (textarea) {{
                            textarea.value = tamMetin.trim();
                            textarea.dispatchEvent(new Event('input', {{ bubbles: true }}));
                            statusBox.innerHTML = "🎉 Video dökümü (Mevcut Dil) başarıyla alındı! 'Metni Analiz Et' butonuna basabilirsiniz.";
                        }}
                    }} else {{
                        statusBox.innerHTML = "💡 Altyazı katmanı doğrudan çözülemedi. Lütfen metni aşağıdaki alana kopyalayarak analizi tamamlayın.";
                        statusBox.style.backgroundColor = "#fff3e0";
                        statusBox.style.color = "#e65100";
                    }}
                }});
            }}
        }})
        .catch(err => {{
            statusBox.innerHTML = "💡 Altyazı katmanı doğrudan çözülemedi. Lütfen metni aşağıdaki alana kopyalayarak analizi tamamlayın.";
            statusBox.style.backgroundColor = "#fff3e0";
            statusBox.style.color = "#e65100";
        }});
    }}
    // API hazır olmama ihtimaline karşı tetikleyici emniyet sigortası
    if(window.YT && window.YT.Player) {{ onYouTubeIframeAPIReady(); }}
    </script>
    """
    components.html(js_bridge_html, height=75)

st.divider()

