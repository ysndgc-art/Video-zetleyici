def ytdlp_altyazi_cek(video_id, cerez_yolu):
    safe_id = str(video_id).strip()
    ydl_opts = {
        'writesubtitles': True,
        'writeautomaticsub': True,
        'subtitleslangs': ['tr', 'en', 'auto', 'tr-orig', 'en-orig', '.*'],  # Tüm dil varyasyonlarını zorla
        'skip_download': True,
        'cookiefile': cerez_yolu,
        'outtmpl': f"sub_{safe_id}",
        'quiet': True,
        'no_warnings': True,
        'ie_key': 'Youtube'
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([safe_id])
        
        bulunan_dosya = None
        # Dizinde bu video ID'sine ait VTT veya SRT dosyasını tara
        for dosya in os.listdir("."):
            if dosya.startswith(f"sub_{safe_id}") and (dosya.endswith(".vtt") or dosya.endswith(".srt")):
                bulunan_dosya = dosya
                break
                
        if bulunan_dosya and os.path.exists(bulunan_dosya):
            indirilen_dil = "en" if ".en" in bulunan_dosya.lower() else "tr"
            with open(bulunan_dosya, "r", encoding="utf-8") as f:
                icerik = f.read()
            
            lines = icerik.split("\n")
            temiz_satirlar = []
            for line in lines:
                # VTT / SRT formatına ait zaman damgalarını ve meta verileri temizle
                if "-->" not in line and line.strip() and not line.strip().isdigit() and "WEBVTT" not in line and "Kind:" not in line and "Language:" not in line:
                    clean_line = re.sub(r'<[^>]*>', '', line).strip()
                    if clean_line and (not temiz_satirlar or temiz_satirlar[-1] != clean_line):
                        temiz_satirlar.append(clean_line)
                        
            try: os.remove(bulunan_dosya)
            except: pass
            
            if temiz_satirlar:
                return " ".join(temiz_satirlar), indirilen_dil
    except Exception as e:
        pass
    return None, "tr"
