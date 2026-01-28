# Fix Memory Leaks — browser_agent

**Приоритет:** Critical
**Контекст:** Процесс python3.12 (browser_agent) потреблял 30 ГБ RAM при 24 ГБ физической памяти, вызывая swap thrashing и зависания системы. Ниже — конкретные проблемы и требования к исправлению.

---

## 1. Unbounded URL History

**Файлы:**
- `src/browser_agent/agents/planner.py:27` — `self._url_history: list[str] = []`
- `src/browser_agent/core/recovery.py:462` — `self._url_history: list[str] = []`

**Проблема:** Списки растут бесконечно через `.append()` без ограничений.

**Исправление:** Заменить `list` на `collections.deque(maxlen=N)` с разумным лимитом (например, 200). Убедиться, что остальной код совместим с deque (индексация, итерация).

---

## 2. Скриншоты без очистки

**Файлы:**
- `src/browser_agent/tools/screenshot.py:32-46` — создаёт PNG без удаления
- `src/browser_agent/tools/hybrid_observe.py:39-54` — base64-кодирует в память

**Проблема:**
- Скриншоты накапливаются на диске и в памяти.
- Base64-кодирование даёт +33% overhead и хранится в памяти до завершения API-вызова.
- Уже 15+ скриншотов в корне проекта.

**Исправление:**
- Использовать `tempfile.NamedTemporaryFile` или явно удалять после обработки.
- В `hybrid_observe.py`: удалять файл после base64-кодирования.
- Удалить накопившиеся `screenshot-*.png` из корня проекта (добавить в `.gitignore`).

---

## 3. Browser context не закрывается при ошибках

**Файл:** `scripts/eval.py` (основной цикл запуска задач)

**Проблема:** Нет `try-finally` для гарантированного вызова `context.close()` / `browser.close()`. При exception Chromium остаётся висеть в памяти. Каждый незакрытый инстанс — 300 МБ-1 ГБ.

**Исправление:**
- Обернуть запуск задач в `try-finally` с гарантированным `context.close()` и `browser.close()`.
- Рассмотреть context manager (`async with`) для Playwright ресурсов.
- Проверить все точки выхода — нормальный, exception, keyboard interrupt.

---

## 4. Persistent browser profile растёт без лимита

**Путь:** `~/.browser-agent/demo-session/` (21 МБ и растёт)

**Проблема:** `launch_persistent_context()` хранит кэши, cookies, GPU shader cache без очистки.

**Исправление:**
- Добавить опцию очистки кэша между запусками (не cookies — они нужны для сессий).
- Очищать `GraphiteDawnCache/`, `ShaderCache/`, `GrShaderCache/` при старте или по флагу.
- Либо добавить `--clean-cache` флаг в CLI.

---

## 5. Context tracker — потенциальная утечка

**Файл:** `src/browser_agent/core/context.py`

**Проблема:** `_tokens_by_category` dict и action history растут с каждым действием. `max_history_length=50` может не применяться корректно.

**Исправление:**
- Проверить, что `max_history_length` реально обрезает историю.
- `_tokens_by_category` — убедиться, что старые записи удаляются.
- `_current_snapshot` — не держать ссылки на старые PageSnapshot.

---

## 6. Общие улучшения

- [ ] Добавить `screenshot-*.png` в `.gitignore`
- [ ] Удалить существующие `screenshot-*.png` из корня
- [ ] Добавить лог предупреждение при RSS > 2 ГБ (опционально, через `resource.getrusage`)
- [ ] Убедиться, что тесты (`pytest`) не оставляют zombie-процессы Chromium

---

## Порядок выполнения

1. Пункты 1-2 (быстрые фиксы, максимальный эффект)
2. Пункт 3 (eval.py cleanup)
3. Пункт 5 (context tracker)
4. Пункты 4, 6 (качество жизни)

## Валидация

После фиксов запустить `uv run pytest` и мониторить RSS процесса — не должен превышать ~2 ГБ на тестах и ~4 ГБ на eval с реальными задачами.
