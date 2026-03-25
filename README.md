# AirGuard Uzbekistan v1

Это первый шаг из single-file демо в реальную рабочую программу.

## Что внутри
- `backend/app/main.py` — FastAPI proxy
- `frontend/index.html` — живой фронтенд
- `/api/realtime/summary?city=tashkent` — единый endpoint

## Как запускать локально
1. Перейдите в `backend`
2. Создайте `.env` на основе `.env.example`
3. Установите зависимости:
   `pip install -r requirements.txt`
4. Запустите:
   `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`

## Что нужно дальше
- хранение исторических данных в БД
- авторизация
- карта районов
- правила уведомлений
- роли: user / city / enterprise
