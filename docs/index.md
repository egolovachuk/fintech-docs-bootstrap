---
id: index
title: Быстрый старт
slug: /
---

# Первый платёж за 5 минут

Цель этой страницы — ваш первый ответ `201 Created`. Всё остальное потом.

## 1. Получите ключ sandbox

Ключи выдаются в личном кабинете: раздел *Разработчикам → API-ключи*.
Sandbox-ключи начинаются с `sk_test_`.

## 2. Создайте платёж

```bash
curl -X POST https://sandbox.api.example/v1/payments \
  -H "Authorization: Bearer sk_test_ВАШ_КЛЮЧ" \
  -H "Content-Type: application/json" \
  -d '{"amount": 120000, "currency": "RUB", "customer_id": "c_demo"}'
```

Ответ:

```json
{ "id": "pay_01H...", "status": "processing", "amount": 120000 }
```

## 3. Проверьте статус

```bash
curl https://sandbox.api.example/v1/payments/pay_01H... \
  -H "Authorization: Bearer sk_test_ВАШ_КЛЮЧ"
```

Получили `settled` — интеграция дышит. Дальше:
**[Сценарии](/scenarios)** — как из ручек собираются бизнес-процессы,
**[Аутентификация](/authentication)** — до выхода в прод.
