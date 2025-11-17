import streamlit as st
import requests
import json
from io import BytesIO

API_URL = "http://127.0.0.1:8000/upload-pdf/"

# --- STREAMLIT SAYFA AYARLARI ---
st.set_page_config(
    page_title="Otomatik Makale Özetleyici (MVP)",
    layout="wide",
    initial_sidebar_state="expanded"
)

def format_summary(summary_data):
    """LLM'den gelen yapılandırılmış JSON veriyi Streamlit'te gösterilecek şekilde biçimlendirir."""
    
    st.subheader("📚 Yapılandırılmış Makale Özeti")

    # Kategori Etiketi
    category = summary_data.get('kategori', 'Bilinmiyor')
    st.markdown(f"**🏷️ Kategori:** <span style='background-color:#5a9ee0; color:white; padding: 5px 10px; border-radius: 8px; font-weight: bold;'>{category}</span>", unsafe_allow_html=True)
    st.markdown("---")

    # Genel Özet (Daha Görünür)
    st.info(summary_data.get('ozet_genel', 'Genel özet çıkarılamadı.'))
    st.markdown("---")

    # Ana Bölümler (Genişletilebilir Alanlar)
    with st.expander("🔬 Metodoloji ve Yöntem"):
        st.write(summary_data.get('metodoloji', 'Bilgi bulunamadı.'))

    with st.expander("📊 Veri Seti Detayları"):
        st.write(summary_data.get('veri_seti', 'Bilgi bulunamadı.'))

    with st.expander("⭐ Ana Sonuçlar ve Bulgular"):
        st.write(summary_data.get('sonuclar', 'Bilgi bulunamadı.'))
        
    st.markdown("---")
    st.caption("Veriler, Mistral-7B-Instruct-v0.2 modeli kullanılarak otomatik olarak çıkarılmıştır.")


def main():
    st.title("Otomatik Makale Analiz ve Özetleme Uygulaması")
    st.markdown("Makalenizi yükleyin, biz sizin için ana bileşenlerini (Metot, Veri Seti, Sonuçlar) ve genel özetini çıkaralım.")
    
    # Dosya yükleyici bileşeni
    uploaded_file = st.file_uploader("PDF Makalenizi Buraya Sürükleyin veya Tıklayın", type=["pdf"])

    if uploaded_file is not None:
        # 1. Yüklenen dosyayı FastAPI'ye göndermek için hazırlayın
        # requests kütüphanesi için dosya formatı (dosyanın adı ve içeriği)
        files = {
            "file": (uploaded_file.name, uploaded_file.getvalue(), "application/pdf")
        }
        
        st.info("Makaleniz yükleniyor... Özet çıkarılması LLM çağrısı nedeniyle 5-30 saniye sürebilir.")
        
        # Dönüşüm işlemi bitene kadar bir yükleme animasyonu göster
        with st.spinner('Makale analiz ediliyor ve yapılandırılmış özet çıkarılıyor...'):
            try:
                # 2. FastAPI API'ye POST isteği gönder
                response = requests.post(API_URL, files=files)
                
                # 3. Yanıtı Kontrol Etme
                if response.status_code == 200:
                    data = response.json()
                    
                    # Başarılı JSON yanıtı alındıysa
                    if data.get('status') == 'Success':
                        format_summary(data['summary'])
                    else:
                        st.error("API'den beklenen özet verisi alınamadı.")
                
                elif response.status_code == 400:
                    # Kötü istek (örneğin dosya çok kısaysa)
                    error_detail = response.json().get('detail', 'Hata: PDF formatı geçersiz veya metin çok kısa.')
                    st.error(f"İşlem Hatası (400): {error_detail}")

                else:
                    # Diğer sunucu hataları (500)
                    error_detail = response.json().get('detail', 'API sunucusunda bilinmeyen bir hata oluştu.')
                    st.error(f"API Sunucu Hatası ({response.status_code}): {error_detail}. Lütfen terminaldeki logları kontrol edin.")
            
            except requests.exceptions.ConnectionError:
                st.error("Bağlantı Hatası: Lütfen FastAPI sunucusunun (uvicorn) arka planda çalıştığından emin olun.")
            except Exception as e:
                st.error(f"Beklenmedik bir hata oluştu: {e}")

if __name__ == "__main__":
    main()