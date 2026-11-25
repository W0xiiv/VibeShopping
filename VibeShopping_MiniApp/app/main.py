import base64
import hashlib
import hmac
import json
import os
import time
from urllib.parse import parse_qsl, quote_plus

from dotenv import load_dotenv
from fastapi import FastAPI, File, Header, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from openai import AsyncOpenAI

load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
AI_API_KEY = os.getenv("AI_API_KEY", "")
AI_BASE_URL = os.getenv("AI_BASE_URL") or None
AI_MODEL = os.getenv("AI_MODEL", "gpt-4o-mini")
MAX_IMAGE_BYTES = 8 * 1024 * 1024

app = FastAPI(title="VibeShopping API")
app.mount("/static", StaticFiles(directory="app/static"), name="static")
ai = AsyncOpenAI(api_key=AI_API_KEY, base_url=AI_BASE_URL) if AI_API_KEY else None


def validate_telegram_init_data(init_data: str) -> dict:
    """Validate Telegram Mini App initData before trusting user identity."""
    if not BOT_TOKEN:
        raise HTTPException(500, "Сервер не настроен: отсутствует токен бота")
    try:
        pairs = dict(parse_qsl(init_data, keep_blank_values=True))
        received_hash = pairs.pop("hash", None)
        if not received_hash:
            raise ValueError("Missing hash")
        data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(pairs.items()))
        secret_key = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
        calculated_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(calculated_hash, received_hash):
            raise ValueError("Invalid hash")
        auth_date = int(pairs.get("auth_date", "0"))
        if abs(time.time() - auth_date) > 24 * 60 * 60:
            raise ValueError("Expired initData")
        user = json.loads(pairs.get("user", "{}"))
        return user
    except Exception:
        raise HTTPException(401, "Не удалось подтвердить данные Telegram. Перезапусти приложение.")


def make_links(query: str) -> dict:
    q = quote_plus(query)
    return {
        "Wildberries": f"https://www.wildberries.ru/catalog/0/search.aspx?search={q}",
        "Ozon": f"https://www.ozon.ru/search/?text={q}",
        "Яндекс Маркет": f"https://market.yandex.ru/search?text={q}",
    }


@app.get("/")
async def index():
    return FileResponse("app/static/index.html")


@app.get("/health")
async def health():
    return {"ok": True, "service": "VibeShopping"}


@app.post("/api/analyze")
async def analyze(
    photo: UploadFile = File(...),
    x_telegram_init_data: str = Header(default="")
):
    validate_telegram_init_data(x_telegram_init_data)
    if ai is None:
        raise HTTPException(503, "Не настроен AI_API_KEY на сервере")
    if photo.content_type not in ("image/jpeg", "image/png", "image/webp"):
        raise HTTPException(415, "Поддерживаются JPG, PNG и WEBP")
    content = await photo.read()
    if not content or len(content) > MAX_IMAGE_BYTES:
        raise HTTPException(413, "Изображение пустое или больше 8 МБ")

    mime = photo.content_type
    image_b64 = base64.b64encode(content).decode("ascii")
    prompt = """
Определи по фото потребительский товар и предложи запросы для поиска аналогов
в российских интернет-магазинах. Не угадывай невидимый бренд или модель.
Ответь строго JSON:
{
 "name":"название товара",
 "category":"категория",
 "visible_features":["до 5 характеристик, видимых на фото"],
 "search_queries":["2-3 поисковых запроса для аналогов"],
 "confidence_note":"короткое пояснение неопределённости"
}
Ищи именно аналоги по назначению и видимым характеристикам, а не только по внешнему виду.
"""
    try:
        response = await ai.chat.completions.create(
            model=AI_MODEL,
            response_format={"type": "json_object"},
            temperature=0.2,
            messages=[
                {"role": "system", "content": "Ты аккуратный помощник по подбору товаров. Не выдумывай характеристики, цены, отзывы или рейтинги."},
                {"role": "user", "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{image_b64}", "detail": "high"}}
                ]}
            ]
        )
        data = json.loads(response.choices[0].message.content or "{}")
        queries = data.get("search_queries") or [data.get("name", "товар")]
        query = str(queries[0])
        return {
            "name": data.get("name", "Товар"),
            "category": data.get("category", "Не определена"),
            "features": data.get("visible_features", []),
            "queries": queries[:3],
            "confidence_note": data.get("confidence_note", ""),
            "links": make_links(query)
        }
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(502, "Не удалось распознать изображение. Попробуй ещё раз.")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=int(os.getenv("PORT", "8000")))
