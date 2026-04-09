# Auth Service — JWT + Redis (Белый/Чёрный список)

Тестовое задание: реализация системы аутентификации и авторизации с использованием JWT и Redis для управления белым и чёрным списком токенов.

---

## Оглавление

- [Архитектура](#архитектура)
- [Стек технологий](#стек-технологий)
- [Запуск проекта](#запуск-проекта)
- [API Reference](#api-reference)
- [Система токенов: белый и чёрный список](#система-токенов-белый-и-чёрный-список)
- [Система ролей и контент](#система-ролей-и-контент)
- [Взаимодействие с контентом — выбор подхода](#взаимодействие-с-контентом--выбор-подхода)
- [Безопасность: утечки токенов](#безопасность-утечки-токенов)
- [Структура проекта](#структура-проекта)

---

## Архитектура

Проект построен по принципам **Clean Architecture** с разделением на слои:

```
Client
  │
  ├──► Авторизация (Auth Service)
  │       ├── Белый список (Redis whitelist:users:{user_id})
  │       └── Чёрный список (Redis blacklist:token:{token})
  │
  └──► Контент (Content Router)
          ├── /content/common  — общий для admin + user
          ├── /content/admin   — только admin
          ├── /content/user    — только user
          └── /content/all     — публичный, без авторизации
```

### Слои приложения

| Слой | Директория | Ответственность |
|------|-----------|-----------------|
| **Core** | `src/core/` | Доменные модели, абстрактные репозитории |
| **Application** | `src/application/` | Use Cases, DTO, Mappers |
| **Infrastructure** | `src/infrastructure/` | БД, Redis, JWT |
| **Interfaces** | `src/interfaces/api/` | FastAPI роуты, зависимости |

---

## Стек технологий

- **FastAPI** — веб-фреймворк (async)
- **SQLAlchemy 2.0 (asyncpg)** — ORM + async PostgreSQL
- **Redis** — хранение белого/чёрного списков токенов
- **python-jose** — генерация и валидация JWT
- **passlib[bcrypt]** — хэширование паролей
- **Alembic** — миграции БД
- **Docker + Docker Compose** — контейнеризация

---

## Запуск проекта

### Через Docker Compose (рекомендуется)

```bash
# Клонировать / распаковать проект
cp .env.example .env   # задать переменные окружения

docker compose up --build
```

Сервис будет доступен на `http://localhost:8000`.  
Swagger UI: `http://localhost:8000/docs`

### Локально (без Docker)

```bash
# Требуется: Python 3.13+, запущенные PostgreSQL и Redis

pip install poetry
poetry install

# Применить миграции
alembic upgrade head

# Запуск
python -m run.main
```

### Переменные окружения (`.env`)

```env
DB_USER=myuser
DB_PASSWORD=mypassword
DB_HOST=db
DB_PORT=5432
DB_NAME=mydatabase
DB_ECHO=false

JWT_SECRET_KEY=<случайная-строка-минимум-32-символа>
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

REDIS_URL=redis://redis:6379/0
```

---

## API Reference

### Аутентификация

#### `POST /dummylogin`
Быстрый вход без пароля — для демонстрации и тестирования.

```json
// Request
{ "role": "admin" }   // или "user"

// Response
{ "token": "<jwt>" }
```

#### `POST /register`
Регистрация нового пользователя.

```json
// Request
{ "email": "user@example.com", "password": "secret", "role": "user" }

// Response 201
{ "id": "uuid", "email": "user@example.com", "role": "user" }
```

#### `POST /login`
Вход по email + пароль. Выдаёт JWT, который записывается в белый список Redis.

```json
// Request
{ "email": "user@example.com", "password": "secret" }

// Response
{ "token": "<jwt>" }
```

#### `POST /logout`
Инвалидация токена: токен добавляется в чёрный список, запись в белом списке удаляется.

```
Authorization: Bearer <token>
```

### Контент

Все `/content/*` роуты требуют заголовка `Authorization: Bearer <token>`.

| Эндпоинт | Роли | Описание |
|----------|------|----------|
| `GET /content/all` | все (без авторизации) | Публичный контент |
| `GET /content/common` | admin, user | Общий для всех авторизованных |
| `GET /content/admin` | admin | Только для администратора |
| `GET /content/user` | user | Только для обычного пользователя |

---

## Система токенов: белый и чёрный список

### Белый список (`whitelist:users:{user_id}`)

Хранится только **один** актуальный токен на пользователя. При каждом успешном входе (`/login`, `/dummylogin`) выполняется следующая последовательность:

```
1. GET whitelist:users:{user_id}          → читаем старый токен (если есть)
2. SET blacklist:token:{old_token} EX ttl → явно отзываем старый токен
3. SET whitelist:users:{user_id} <new_token> EX 600 → записываем новый
```

Это покрывает сценарий **повторного логина без logout**: старый токен не просто вытесняется из whitelist, а явно попадает в blacklist. Это означает, что если кто-то украл старый токен и использует его параллельно — он будет немедленно отклонён по blacklist, а не только по несовпадению в whitelist.

При проверке каждого запроса:
1. Токен декодируется, из него берётся `user_id`
2. Из Redis читается `whitelist:users:{user_id}`
3. Если токены не совпадают → ошибка `token superseded`

### Чёрный список (`blacklist:token:{token}`)

Токен попадает в blacklist в двух случаях:

**При logout:**
```
SET blacklist:token:{raw_jwt}  "1"  EX <remaining_ttl>
DEL whitelist:users:{user_id}   ← сессия закрыта, нового токена нет
```

**При повторном логине (без logout):**
```
SET blacklist:token:{old_token}  "1"  EX <remaining_ttl>
SET whitelist:users:{user_id}  <new_token>  EX 600   ← перезапись, не удаление
```

Обрати внимание на разницу: при logout whitelist **удаляется** (`DEL`), при повторном логине — **перезаписывается** (`SET`). Лишний `DEL` перед `SET` был бы бессмысленной операцией.

TTL ключа blacklist всегда равен оставшемуся времени жизни токена — Redis сам чистит истёкшие записи.

### Порядок проверки в `get_current_user`

```
1. decode_token() → проверка подписи и срока действия
2. redis.exists(blacklist:token:{token}) → если есть → 401 "token revoked"
3. redis.get(whitelist:users:{user_id}) → если пусто → 401 "session expired"
4. stored_token == token → если нет → 401 "token superseded"
```

---

## Система ролей и контент

Роли задаются при регистрации и хранятся в JWT payload:

```json
{ "user_id": "uuid", "role": "admin", "exp": 1234567890 }
```

Проверка роли реализована через фабрику зависимостей `require_role(*roles)`:

```python
@router.get("/admin")
async def admin(user=Depends(require_role("admin"))):
    ...
```

### Матрица доступа

| Эндпоинт | admin | user | anonymous |
|----------|:-----:|:----:|:---------:|
| `/content/all` | ✅ | ✅ | ✅ |
| `/content/common` | ✅ | ✅ | ❌ |
| `/content/admin` | ✅ | ❌ | ❌ |
| `/content/user` | ❌ | ✅ | ❌ |

---

## Взаимодействие с контентом — выбор подхода

**Выбранный подход: JWT + Redis (stateful whitelist)**

Рассматривались три варианта:

### 1. Чистый stateless JWT
Плюсы: нет внешних зависимостей, горизонтально масштабируется.  
Минусы: невозможно отозвать токен до истечения TTL — украденный токен работает до expire.

### 2. Opaque tokens (хранение сессий целиком в Redis)
Плюсы: полный контроль над сессиями.  
Минусы: каждый запрос — поход в Redis + нет стандартного формата, нужна своя библиотека.

### 3. JWT + Redis whitelist/blacklist ✅ (выбран)
Плюсы:
- JWT остаётся самодостаточным (роль внутри, не нужен лишний DB-запрос)
- Возможность моментального отзыва токена через чёрный список
- Обнаружение кражи через вытеснение (один токен на сессию)
- Redis хранит только лёгкие ключи, а не полные пользовательские данные

Минусы: зависимость от Redis (решается репликацией/sentinel).

**Вывод:** это оптимальный баланс между производительностью и безопасностью для большинства production-систем.

---

## Безопасность: утечки токенов

### Как токен может быть украден

1. **XSS** — вредоносный JS читает токен из `localStorage`
2. **MITM** — перехват незашифрованного HTTP-трафика
3. **Компрометация клиента** — вирус, keylogger, утечка логов
4. **Log injection** — токен попадает в логи сервера в открытом виде
5. **Shared environments** — токен в переменных окружения на CI/CD

### Как обнаружить, что токен украден

**Вытеснение сессии с явным отзывом (реализовано в проекте):**  
Каждый новый логин читает старый токен из whitelist и явно кладёт его в blacklist перед выдачей нового. Это значит: если пользователь залогинился повторно без logout, старый токен заблокирован сразу по двум механизмам — его нет в whitelist и он есть в blacklist. Украденный старый токен будет отклонён немедленно, а не только при несовпадении в whitelist.

**Дополнительные методы (не реализованы, но рекомендованы):**

- **Fingerprinting:** при выдаче токена сохранять User-Agent + IP; при каждом запросе сравнивать — резкое изменение = подозрение на кражу
- **Refresh token rotation:** короткий access + длинный refresh; при использовании refresh — старый инвалидируется; повторное использование старого refresh → немедленный logout всех сессий
- **Аномалии:** geo-velocity detection (логин из Москвы, через 5 минут запрос из Токио)

### Способы защиты

| Угроза | Защита |
|--------|--------|
| XSS | Хранить токены в `httpOnly` cookie, не в `localStorage` |
| MITM | HTTPS строго обязателен (HSTS) |
| Долгоживущий токен | Короткий TTL (10-30 мин) + refresh-токены |
| Параллельные сессии | Single-session whitelist (реализовано) |
| Украденный токен работает | Blacklist при logout и при повторном логине (реализовано) |
| Утечка секрета | `JWT_SECRET_KEY` из env, ротация ключей |

---

## Структура проекта

```
test_psek/
├── run/
│   └── main.py                  # Точка входа FastAPI
├── src/
│   ├── core/                    # Домен
│   │   ├── domain/models.py     # Доменные модели (dataclass)
│   │   └── repositories.py      # Абстрактные репозитории (ABC)
│   ├── application/             # Бизнес-логика
│   │   ├── dto/auth.py          # Pydantic схемы
│   │   ├── mappers/user.py      # DB → Domain → DTO
│   │   └── use_case/auth.py     # Login, Register, Logout, DummyLogin
│   ├── infrastructure/          # Внешние зависимости
│   │   ├── auth/jwt.py          # Создание/декодирование JWT
│   │   ├── cache/redis_client.py# Клиент Redis
│   │   └── database/            # SQLAlchemy, модели, репозитории
│   ├── interfaces/
│   │   └── api/
│   │       ├── auth.py          # /login, /register, /logout, /dummylogin
│   │       ├── content.py       # /content/* роуты
│   │       └── dependencies.py  # get_current_user, require_role
│   ├── config/settings.py       # Pydantic Settings
│   └── migrations/              # Alembic
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
└── .env.example
```

---

## Известные ограничения и точки роста

- **Refresh-токены не реализованы** — при истечении access-токена нужен повторный логин. В production рекомендуется добавить refresh-цикл.
- **Одна сессия на пользователя** — по задумке. Для multi-device нужно хранить `whitelist:users:{user_id}:{device_id}`.
- **Fingerprinting не реализован** — добавление User-Agent/IP в проверку значительно повысит обнаружение краж.
- **Тесты** — зависимости для pytest подключены, но тест-файлы не реализованы.
