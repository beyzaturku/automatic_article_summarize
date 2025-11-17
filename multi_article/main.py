import io
import os
import json
import traceback
from typing import List, Dict, Any

from dotenv import load_dotenv
from pydantic import BaseModel, Field
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from google import genai
from google.genai import types
import pdfplumber

load_dotenv()

GEMINI_MODEL = "gemini-2.0-flash"

try:
    client = genai.Client()
    print(f"Gemini modeli hazır: {GEMINI_MODEL}")
except Exception as e:
    print(f"Gemini istemcisi başlatılamadı. Ortam değişkenlerini kontrol edin: {e}")
    client = None

class ArticleSummary(BaseModel):
    veri_seti: str = Field(description="Çalışmada kullanılan veri setinin adı, boyutu ve kaynağı hakkında kısa bilgi.")
    metodoloji: str = Field(description="Uygulanan temel yöntem, algoritma ve yenilikçi yaklaşımların kısa açıklaması.")
    sonuclar: str = Field(description="Elde edilen en önemli bulgular, metrikler ve ana çıkarımlar.")
    kategori: str = Field(description="Makalenin ana konusunu (Örn: NLP, CV, RL, Hardware, Teorik) içeren tek kelime.")
    ozet_genel: str = Field(description="Makalenin genel amacını, yöntemini ve sonuçlarını kapsayan 3-4 cümlelik standart özet.")

app = FastAPI(
    title="Çoklu Makale Özetleyici ve Analiz API'si",
    description="Çoklu PDF yükleyerek yapılandırılmış özet ve kategori çıkaran API. Başarısız dosyalara rağmen diğerlerini işlemeye devam eder."
)

@app.get("/")
def read_root():
    return {"message": "Çoklu PDF Özetleme API'si Hazır!"}

def _extract_text_from_pdf(contents: bytes) -> str:
    """PDF içeriğinden metin çıkarır ve temizler."""
    with pdfplumber.open(io.BytesIO(contents)) as pdf:
        extracted_text = ""
        MAX_PAGES = 10  # İlk 10 sayfayı alarak modeli hızlandırmak ve maliyeti düşürmek
        
        for i, page in enumerate(pdf.pages):
            if i >= MAX_PAGES:
                break
            text = page.extract_text()
            if text:
                extracted_text += text + "\n"
        
        clean_text = " ".join(extracted_text.split()).strip()
        return clean_text
    
def _get_gemini_summary(input_text: str) -> ArticleSummary:
    """Gemini API'yi çağırır ve yapılandırılmış özet döner."""
    
    system_prompt = (
        "Sen bir yapay zeka araştırma asistanısın. "
        "Görevin, sana verilen bilimsel makale metnini analiz ederek "
        "kesinlikle ve sadece aşağıdaki JSON formatında Türkçe özet oluşturmaktır. "
        "Başka hiçbir açıklama, giriş veya çıkış cümlesi ekleme. "
        "Makalenin amacını, yöntemini, veri setini ve sonuçlarını kapsayıcı ol."
        "Makalenin literatürdeki çalışmalardan farkını açıkla."
    )
    
    # Pydantic modelini kullanarak beklenen JSON yapısını oluştur
    json_format_description = ArticleSummary.model_json_schema()
    
    user_prompt = (
        f"MAKALE METNİ:\n{input_text}"
    )

    # Gemini'nin yapılandırılmış yanıt özelliğini kullan
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=user_prompt,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            response_mime_type="application/json",
            response_schema=json_format_description
        )
    )
    
    # API'dan gelen metin (JSON string)
    response_text = response.text.strip()
    
    # Gelen JSON'u parse et
    summary_dict = json.loads(response_text)
    
    # Pydantic modeli ile doğrula
    validated_summary = ArticleSummary(**summary_dict)
    
    return validated_summary

@app.post("/summarize-pdfs", response_model=List[Dict[str, Any]])
async def summarize_pdfs(files: List[UploadFile] = File(...)):
    """
    Birden fazla PDF dosyasını işler ve her biri için yapılandırılmış özet döner.
    Hatalı dosyalar atlanır, diğer dosyalar işlenmeye devam eder.
    """
    if client is None:
        raise HTTPException(
            status_code=503,
            detail="LLM (Gemini) istemcisi başlatılamadı. Sunucu loglarını kontrol edin."
        )

    all_summaries = []
    MAX_CHARACTERS = 15000 
    
    for file in files:
        filename = file.filename
        
        # Her bir dosya için bağımsız try-except bloğu
        try:
            print(f"[{filename}] - İşleniyor...")
            
            # 1. Dosya Kontrolü
            if file.content_type != "application/pdf":
                raise ValueError("Yalnızca PDF formatındaki dosyalar kabul edilir.")
            
            # 2. Dosya içeriğini belleğe oku
            contents = await file.read()
            
            # 3. pdfplumber ile metin çıkarma ve temizleme
            clean_text = _extract_text_from_pdf(contents)
            
            if len(clean_text) < 500:
                raise ValueError("PDF'ten yeterli metin çıkarılamadı (Min 500 karakter gerekli).")
            
            # 4. Modele gönderilecek metni limitlendirme
            input_text = clean_text[:MAX_CHARACTERS]
            
            # 5. Gemini API çağrısı ve JSON özetini alma
            validated_summary = _get_gemini_summary(input_text)
            
            # Başarılı sonuç listeye eklenir
            all_summaries.append({
                "filename": filename,
                "status": "Success",
                "text_length": len(clean_text),
                "summary": validated_summary.model_dump(),
                "model_used": GEMINI_MODEL,
                "extracted_text_sample": clean_text[:300] + "..."
            })
            print(f"[{filename}] - Başarıyla tamamlandı.")

        # Hata yakalama: Özelleştirilmiş ve genel hatalar
        except ValueError as e:
            error_detail = str(e)
            print(f"[{filename}] - Hata (Veri Doğrulama): {error_detail}")
            all_summaries.append({
                "filename": filename,
                "status": "Failed",
                "detail": f"Dosya işleme hatası: {error_detail}"
            })
        except json.JSONDecodeError:
            error_detail = "LLM hatalı/geçersiz JSON formatında yanıt verdi."
            print(f"[{filename}] - Hata (JSON Parse): {error_detail}")
            all_summaries.append({
                "filename": filename,
                "status": "Failed",
                "detail": error_detail
            })
        except Exception as e:
            error_detail = f"Beklenmedik bir hata oluştu: {type(e).__name__} - {e}"
            print(f"[{filename}] - Hata (Genel): {error_detail}")
            traceback.print_exc()
            all_summaries.append({
                "filename": filename,
                "status": "Failed",
                "detail": "Sunucu veya API hatası oluştu. Logları kontrol edin."
            })
        finally:
            # Dosya okuma bittikten sonra dosya işaretçisini kapat
            await file.close()

    return all_summaries