import streamlit as st
import requests
import json
from io import BytesIO
from typing import List, Dict
import pdfplumber
from PIL import Image

API_URL = "http://127.0.0.1:8000/summarize-pdfs" 
PREVIEW_API_URL = "http://127.0.0.1:8000/preview-pdf"

st.set_page_config(
    page_title="Çoklu Makale Analiz Asistanı",
    layout="wide",
    initial_sidebar_state="expanded"
)

if 'uploaded_files_data' not in st.session_state:
    st.session_state.uploaded_files_data = {}

def display_summary_in_sidebar():
    """
    Session state'te cache'lenen özetleri yan panelde gösterir.
    """
    st.sidebar.title("📚 Analiz Sonuçları")

    all_results = []
    for filename, data in st.session_state.uploaded_files_data.items():
        result = data.get("summary_cached")
        if result is not None:
            all_results.append(result)

    if not all_results:
        st.sidebar.info("Henüz özetlenmiş makale yok.")
        return

    success_count = sum(1 for item in all_results if item.get("status") == "Success")
    fail_count = len(all_results) - success_count

    if success_count > 0:
        st.sidebar.success(f"{success_count} makale başarıyla özetlendi.")
    if fail_count > 0:
        st.sidebar.error(f"{fail_count} makalede hata oluştu.")

    st.sidebar.markdown("---")

    for result in all_results:
        filename = result.get("filename", "Bilinmeyen Dosya")
        status = result.get("status")

        with st.sidebar.expander(f"{'✅' if status == 'Success' else '❌'} {filename}"):
            if status == "Success":
                summary_data = result["summary"]

                category = summary_data.get("kategori", "Bilinmiyor")
                st.markdown(
                    f"**🏷️ Kategori:** "
                    f"<span style='background-color:#007bff; color:white; padding: 3px 6px; "
                    f"border-radius: 5px; font-size: 0.9em; font-weight: bold;'>{category}</span>",
                    unsafe_allow_html=True,
                )

                st.info(summary_data.get("ozet_genel", "Genel özet çıkarılamadı."))

                st.markdown("**Metodoloji:** " + summary_data.get("metodoloji", "Yok"))
                st.markdown("**Veri Seti:** " + summary_data.get("veri_seti", "Yok"))
                st.markdown("**Sonuçlar:** " + summary_data.get("sonuclar", "Yok"))
            else:
                st.error(result.get("detail", "Bilinmeyen Hata."))

        st.sidebar.markdown("---")

def generate_pdf_preview(file_obj):
    """
    pdfplumber kullanarak PDF'in ilk sayfasından önizleme oluşturur.
    """
    try:
        with pdfplumber.open(BytesIO(file_obj.getvalue())) as pdf:
            # İlk sayfayı al
            first_page = pdf.pages[0]
            
            # Sayfayı PIL Image'e dönüştür
            # pdfplumber'ın to_image() metodu ile
            page_image = first_page.to_image(resolution=150)
            
            # PIL Image nesnesini al
            pil_image = page_image.original
            
            # Boyutu küçült (performans için)
            max_width = 400
            if pil_image.width > max_width:
                ratio = max_width / pil_image.width
                new_height = int(pil_image.height * ratio)
                pil_image = pil_image.resize((max_width, new_height), Image.LANCZOS)
            
            return pil_image
            
    except Exception as e:
        st.warning(f"Önizleme oluşturulamadı: {str(e)}")
        return None

def send_files_to_api(files_to_process: List[Dict]):
    """Seçili dosyaları FastAPI'ye gönderir ve özetleri alır."""
    multi_part_files = [
        ("files", (data["file"].name, data["file"].getvalue(), "application/pdf"))
        for data in files_to_process
    ]

    st.info(
        f"Seçili **{len(files_to_process)}** makale analiz için gönderiliyor. "
        "Lütfen bekleyin..."
    )

    with st.spinner(
        "Makaleler analiz ediliyor ve yapılandırılmış özetler çıkarılıyor..."
    ):
        try:
            response = requests.post(API_URL, files=multi_part_files)

            if response.status_code == 200:
                data = response.json()
                st.success("Analiz tamamlandı. Sonuçlar yan panelde gösteriliyor.")
                return data
            else:
                st.error(
                    f"API Sunucu Hatası ({response.status_code}): "
                    f"{response.json().get('detail', 'Bilinmeyen sunucu hatası.')}"
                )
                return None

        except requests.exceptions.ConnectionError:
            st.error(
                "Bağlantı Hatası: Lütfen FastAPI sunucusunun (uvicorn) "
                "arka planda çalıştığından emin olun."
            )
            return None
        except Exception as e:
            st.error(f"Beklenmedik bir hata oluştu: {e}")
            return None

def main():
    st.title("🔬 Çoklu Literatür Analiz Asistanı")
    st.markdown(
        "Birden fazla PDF makaleyi yükleyin, istediğiniz makaleleri seçin ve "
        "yapılandırılmış özetlerini anında yan panelde görün."
    )

    uploaded_files = st.file_uploader(
        "PDF Makalelerinizi Buraya Sürükleyin veya Tıklayın",
        type=["pdf"],
        accept_multiple_files=True,
    )

    if uploaded_files:
        # Şu an yükleyicide görünen dosya isimleri
        current_filenames = {f.name for f in uploaded_files}

        # Yeni gelen dosyaları session_state'e ekle
        for file in uploaded_files:
            if file.name not in st.session_state.uploaded_files_data:
                st.session_state.uploaded_files_data[file.name] = {
                    "file": file,
                    "selected": False,
                    "summary_cached": None,
                    "preview_image": None,
                }

        # Artık yüklenmeyenleri session_state'ten sil
        for key in list(st.session_state.uploaded_files_data.keys()):
            if key not in current_filenames:
                del st.session_state.uploaded_files_data[key]

        st.subheader("Makale Listesi")

        # Kart sayısı ayarı
        N_CARDS_PER_ROW = 4
        items = list(st.session_state.uploaded_files_data.items())

        # Kartları satırlar halinde göster
        for row_start in range(0, len(items), N_CARDS_PER_ROW):
            row_items = items[row_start : row_start + N_CARDS_PER_ROW]
            cols = st.columns(len(row_items))

            for col, (file_name, data) in zip(cols, row_items):
                with col:
                    card_style = (
                        "border: 2px solid #007bff; border-radius: 10px; "
                        "padding: 10px; margin: 5px; background-color: #f0f8ff;"
                        if data["selected"]
                        else "border: 1px solid #ccc; border-radius: 10px; "
                        "padding: 10px; margin: 5px;"
                    )

                    st.markdown(
                        f'<div style="{card_style}">', unsafe_allow_html=True
                    )

                    st.markdown(f"**📄 {file_name[:25]}...**")
                    st.markdown(
                        f"<small>Boyut: "
                        f"{round(data['file'].size / 1024 / 1024, 2)} MB</small>",
                        unsafe_allow_html=True,
                    )

                    # --- PDF ÖNİZLEME (pdf2image ile) ---
                    if data.get("preview_image") is None:
                        with st.spinner("Önizleme oluşturuluyor..."):
                            preview = generate_pdf_preview(data["file"])
                            if preview is not None:
                                data["preview_image"] = preview

                    if data.get("preview_image") is not None:
                        st.image(data["preview_image"], use_container_width=True)
                    else:
                        st.info("Önizleme oluşturulamadı")

                    # Checkbox (KEY EKLENDİ!) – Her dosya için benzersiz key
                    is_selected = st.checkbox(
                        "Özet İçin Seç",
                        value=data["selected"],
                        key=f"checkbox_{file_name}"
                    )
                    st.session_state.uploaded_files_data[file_name]["selected"] = is_selected

                    st.markdown("</div>", unsafe_allow_html=True)

        # Sadece seçili ve henüz özetlenmemiş dosyalar API'ye gidecek
        selected_files_to_process = [
            data
            for data in st.session_state.uploaded_files_data.values()
            if data["selected"] and data.get("summary_cached") is None
        ]

        if st.button("🚀 Seçili Makaleleri Özetle", type="primary"):
            if not any(
                d["selected"]
                for d in st.session_state.uploaded_files_data.values()
            ):
                st.warning("Lütfen özetlemek istediğiniz en az bir makale seçin.")
            else:
                if not selected_files_to_process:
                    st.info("Seçili makalelerin hepsi için özet mevcut.")
                else:
                    summaries = send_files_to_api(selected_files_to_process)

                    if summaries:
                        for result in summaries:
                            filename = result.get("filename")
                            if filename in st.session_state.uploaded_files_data:
                                st.session_state.uploaded_files_data[filename][
                                    "summary_cached"
                                ] = result

        # Sidebar'da sonuçları göster
        display_summary_in_sidebar()


if __name__ == "__main__":
    main()