import io
import os
import json
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
    print(f"Gemini istemcisi başlatılamadı: {e}")
    client = None 

class ArticleSummary(BaseModel):
    veri_seti: str = Field(description="Çalışmada kullanılan veri setinin adı, boyutu ve kaynağı hakkında kısa bilgi.")
    metodoloji: str = Field(description="Uygulanan temel yöntem, algoritma ve yenilikçi yaklaşımların kısa açıklaması.")
    sonuclar: str = Field(description="Elde edilen en önemli bulgular, metrikler ve ana çıkarımlar.")
    kategori: str = Field(description="Makalenin ana konusunu (Örn: NLP, CV, RL, Hardware, Teorik) içeren tek kelime.")
    ozet_genel: str = Field(description="Makalenin genel amacını, yöntemini ve sonuçlarını kapsayan 3-4 cümlelik standart özet.")

app = FastAPI(
    title = "Otomatik Makale Özetleyici",
    description= "PDF yükleyerek yapılandırılmış özet ve kategori çıkaran API"
)

@app.get("/")
def read_root():
    return {"message": "PDF Yükleme Hazır!"}

@app.post("/upload-pdf")
async def upload_pdf_and_extract_text(file: UploadFile = File(...)):
    if client is None:
        raise HTTPException(
            status_code=503,
            detail="LLM (Mistral) modeli başlatılamadı. Sunucu loglarını kontrol edin."
        )

    # 1. Dosya Kontrolü 
    if file.content_type != "application/pdf":
        raise HTTPException(
            status_code=400,
            detail="Yalnızca PDF formatındaki dosyalar kabul edilir."
        )
    
    try:
    # 2.Dosya içeriğini belleke oku 
        contents = await file.read()

    # 3. pdfplumber ile metin çıkarma 
        with pdfplumber.open(io.BytesIO(contents)) as pdf:
            extracted_text = ""
            MAX_PAGES = 10 

            for i, page in enumerate(pdf.pages):
                if i >= MAX_PAGES:
                    break
                text = page.extract_text()
                if text:
                    extracted_text += page.extract_text() + "\n"
        
        clean_text = " ".join(extracted_text.split()).strip()

        if len(clean_text) < 500:
            raise HTTPException(
                status_code=400,
                detail=f"PDF'ten yeterli metin çıkarılamadı."
            )

        MAX_CHARACTERS = 15000 
        input_text = clean_text[:MAX_CHARACTERS]
        print(f"Başarıyla çıkarılan metin uzunluğu: {len(clean_text)}. Modele gönderilen uzunluk: {len(input_text)}")

        system_prompt = (
            "Sen bir yapay zeka araştırma asistanısın. "
            "Görevin, sana verilen bilimsel makale metnini analiz ederek "
            "kesinlikle ve sadece aşağıdaki JSON formatında Türkçe özet oluşturmaktır. "
            "Başka hiçbir açıklama, giriş veya çıkış cümlesi ekleme."
        )
        
        json_format_description = (
            "{\n"
    ' "veri_seti": "",\n'
    ' "metodoloji": "",\n'
    ' "sonuclar": "",\n'
    ' "kategori": "",\n'
    ' "ozet_genel": ""\n'
    "}"
        )

        user_prompt = (
            f"{system_prompt}\n\n"
            f"Beklenen JSON Formatı:\n{json_format_description}\n\n"
            f"MAKALE METNİ:\n{input_text}"
        )

        try: 
            gemini_response = client.models.generate_content(
                model = GEMINI_MODEL,
                contents = user_prompt,
            )
            response_text = gemini_response.text.strip()
        
        except Exception as e:
            print(f"Gemini API Hatası: {e}")
            raise HTTPException(
                status_code=500,
                detail="Gemini API çağrısında hata oluştu."
            )

    # JSON kod bloğu varsa temizle
        if response_text.startswith("```json"):
            response_text = response_text.replace("```json", "").replace("```", "").strip()
        elif response_text.startswith("```"):
            response_text = response_text.replace("```", "").strip()
        
    # JSON'u parse et
        summary_dict = json.loads(response_text)

    # Pydantic modeli ile doğrula
        validated_summary = ArticleSummary(**summary_dict)

        return JSONResponse(content={
            "filename": file.filename,
            "text_length": len(clean_text),
            "summary": validated_summary.model_dump(),
            "status" : "Success",
            "model_used": GEMINI_MODEL,
            "extracted_text_sample": clean_text[:300] + "..."
        })
    
    # Gemini API hataları yerine genel ve JSON hataları yakalanır
    except json.JSONDecodeError as e:
        print(f"JSON Parse Hatası: {e}")
        print(f"LLM Yanıtı: {response_text if 'response_text' in locals() else 'Yanıt alınamadı'}")
        raise HTTPException(
            status_code=500, 
            detail="LLM hatalı formatta yanıt verdi. Lütfen tekrar deneyin."
        )
    except Exception as e:
        print(f"Genel Hata: {type(e).__name__} - {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500, 
            detail=f"Beklenmedik hata: {str(e)}"
        )
    finally:
        await file.close()

