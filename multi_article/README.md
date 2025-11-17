# 📄 Otomatik Makale Analizi ve Özetleyici (End-to-End LLM Çözümü)
Bu proje, yapay zeka (LLM) teknolojilerini kullanarak PDF biçimindeki bilimsel makaleleri otomatik olarak analiz eder ve yapılandırılmış bir özete dönüştürür. 
Modeli harici bir API'ye bağımlı olmadan, tamamen yerli (kendi sunucusunda) çalıştırılan bir LLM üzerine kurulmuştur.

Bu proje, End-to-End bir çözüm sunar: 
Veri İşleme (PDF Parsing) -> Yapılandırılmış LLM İzleme -> Dağıtılabilir API (FastAPI) -> Kullanıcı Arayüzü (Streamlit) -> Docker 

# 🚀 Canlı Demo
Projenin çalışan versiyonunu [BURAYA YAYINLADIĞINIZ HUGGING FACE / RENDER URL'SİNİ EKLEYİN] adresinden deneyimleyebilirsiniz.

# 🛠️ Teknoloji Yığını (Tech Stack)
<table>
  <thead>
    <tr>
      <th>Modül</th>
      <th>Teknoloji</th>
      <th>Açıklama</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>Model (LLM)</td>
      <td>Mistral-7B-Instruct-v0.2 (Hugging Face)</td>
      <td>Yerel ve kotasız çalışan, 7 milyar parametreli Instruction-Tuned model.</td>
    </tr>
    <tr>
      <td>Backend API</td>
      <td>FastAPI</td>
      <td>Yüksek performanslı, asenkron Python web çerçevesi. PDF yükleme ve LLM ile iletişimi yönetir.</td>
    </tr>
    <tr>
      <td>Frontend UI</td>
      <td>Streamlit</td>
      <td>Hızlı prototipleme ve model çıktısının görselleştirilmesi için Python tabanlı arayüz.</td>
    </tr>
    <tr>
      <td>Veri İşleme</td>
      <td>pdfplumber</td>
      <td>PDF dosyalarından metin çıkarma.</td>
    </tr>
    <tr>
      <td>Konteynerleştirme</td>
      <td>Docker</td>
      <td>Uygulamanın ve model ağırlıklarının her ortamda (CPU/GPU) aynı şekilde çalışmasını sağlar.</td>
    </tr>
    <tr>
      <td>Dağıtım (Ops.)</td>
      <td>Hugging Face Spaces / Render</td>
      <td>Kolay ve ücretsiz yayınlama platformları.</td>
    </tr>
  </tbody>
</table>

# ⚙️ Yerel Kurulum ve Çalıştırma

**Ön Koşullar**
1. Python 3.11+
2. Docker Desktop (Konteyner çalıştırmak için)
3. Minimum 8GB RAM (Model bellekte çalışır)

**Adımlar**
**1. Adım - Depoyu Klonla:**
```bash
git clone [DEPO ADRESİNİZ]
cd automatic_article_summarize
```

**2.Adım - Docket İmajını İnşa Et:**
```bash
# Bu komut, modeli (yaklaşık 5 GB) indirir ve imajı oluşturur.
docker build -t makale-ozetleyici-mvp .
```

**3.Adım - Konteyneri Başlat:**
```bash
# FastAPI (8000) ve Streamlit (8501) portlarını açar
docker run -p 8501:8501 makale-ozetleyici-mvp
```

*Uygulama başlatıldıktan sonra tarayıcınızdan http://localhost:8501 adresine giderek kullanabilirsiniz.*

# 🧠 LLM Mühendisliği (Önemli)
Bu projenin teknik gücü, sadece model kullanmak yerine, yapılandırılmış çıktı garantisi üzerine kurulmuştur:
* **Prompt Mühendisliği:** Modele verilen talimat, çıktının kesinlikle Türkçe JSON formatında olmasını ve belirli anahtarları (veri_seti, metodoloji vb.) içermesini zorlar.
* **JSON Temizleme:** LLM'lerin bazen JSON kod bloğu (```json) ile yanıt vermesi durumuna karşı Python kodu ile yanıt temizlenir ve json.loads ile güvenli bir şekilde ayrıştırılır.