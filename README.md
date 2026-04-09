# Auth Service (JWT + Redis)

Тестовое задание. Реализация аутентификации и авторизации с JWT и Redis — белый и чёрный списки токенов, система ролей, всё упаковано в Docker.

## Оглавление

- [Архитектура](#архитектура)
- [Стек](#стек)
- [Запуск](#запуск)
- [API](#api)
- [Как работают белый и чёрный список](#как-работают-белый-и-чёрный-список)
- [Роли и контент](#роли-и-контент)
- [Почему JWT + Redis](#почему-jwt--redis)
- [Безопасность и утечки токенов](#безопасность-и-утечки-токенов)
- [Структура проекта](#структура-проекта)

---

## Архитектура

Проект написан по Clean Architecture — слои core, application, infrastructure, interfaces. Клиентская часть намеренно минимальна, упор на бэкенд.

```
core/            - доменные модели и абстрактные репозитории
application/     - use cases, dto, mappers
infrastructure/  - база данных, redis, jwt
interfaces/      - fastapi роуты и зависимости
```

Два сервиса: авторизация и контент. Авторизация выдаёт токены и управляет сессиями через Redis. Контент проверяет токен и роль через зависимости FastAPI.

---

## Стек

- Python 3.13, FastAPI
- PostgreSQL + SQLAlchemy 2.0 (async) + asyncpg
- Redis — белый/чёрный список токенов
- python-jose — JWT
- passlib bcrypt — хэши паролей
- Alembic — миграции
- Docker, Docker Compose

---

## Запуск

```bash
cp .env.example .env
# заполнить .env своими значениями

docker compose up --build
```

Swagger: http://localhost:8000/docs

Локально без Docker:

```bash
poetry install
alembic upgrade head
python -m run.main
```

Нужны запущенные PostgreSQL и Redis.

### Переменные окружения

```
DB_USER=
DB_PASSWORD=
DB_HOST=db
DB_PORT=5432
DB_NAME=
DB_ECHO=false

JWT_SECRET_KEY=   # случайная строка, минимум 32 символа
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

REDIS_URL=redis://redis:6379/0
```

.env в репозиторий не коммитить, только .env.example.

---

## API

### POST /dummylogin

Быстрый вход без пароля, для тестирования. Принимает role: "admin" или "user".

```json
{ "role": "admin" }
```

Возвращает токен.

### POST /register

```json
{ "email": "user@example.com", "password": "secret", "role": "user" }
```

Возвращает созданного пользователя, статус 201.

### POST /login

```json
{ "email": "user@example.com", "password": "secret" }
```

Возвращает токен. Если у пользователя уже была активная сессия — старый токен сразу попадает в чёрный список.

### POST /logout

Требует заголовок Authorization: Bearer token. Кладёт токен в чёрный список, удаляет запись из белого.

### GET /content/...

Все контентные роуты требуют валидный токен.

| роут | кто имеет доступ |
|------|-----------------|
| /content/all | все, без авторизации |
| /content/common | admin и user |
| /content/admin | только admin |
| /content/user | только user |

---

## Как работают белый и чёрный список

### Белый список

Ключ в Redis: `whitelist:users:{user_id}`, значение — сам токен, TTL 600 секунд.

На одного пользователя хранится только один токен. При каждом логине:

1. Читаем старый токен из белого списка
2. Если он есть — кладём в чёрный список с оставшимся TTL
3. Записываем новый токен в белый список

Это покрывает сценарий повторного логина без logout. Старый токен не просто вытесняется — он явно отзывается через чёрный список. Если кто-то украл старый токен и пытается им пользоваться параллельно, он будет заблокирован сразу, не дожидаясь истечения TTL.

### Чёрный список

Ключ: `blacklist:token:{raw_jwt}`, значение "1", TTL = остаток жизни токена.

Токен попадает в чёрный список в двух случаях:

Logout:
```
blacklist: SET blacklist:token:{token}  EX remaining_ttl
whitelist: DEL whitelist:users:{user_id}
```

Повторный логин:
```
blacklist: SET blacklist:token:{old_token}  EX remaining_ttl
whitelist: SET whitelist:users:{user_id} {new_token}  EX 600
```

Разница в том, что при logout whitelist удаляется (новой сессии нет), а при повторном логине перезаписывается новым токеном.

### Проверка токена в каждом запросе

1. Декодируем токен, проверяем подпись и срок
2. Проверяем blacklist — если есть, возвращаем 401 "token revoked"
3. Смотрим whitelist — если пусто, 401 "session expired"
4. Сравниваем токены — если не совпадают, 401 "token superseded"

---

## Роли и контент

Роль хранится прямо в JWT payload:

```json
{ "user_id": "uuid", "role": "admin", "exp": 1234567890 }
```

Проверка через фабрику зависимостей `require_role(*roles)`. Можно передать одну роль или несколько:

```python
@router.get("/common")
async def common(user=Depends(require_role("admin", "user"))):
    ...

@router.get("/admin")
async def admin(user=Depends(require_role("admin"))):
    ...
```

Реализовано две роли: admin и user. Есть общий контент для обеих, и отдельный для каждой.

---

## Почему JWT + Redis

Рассматривал три варианта.

**Чистый stateless JWT** — просто, не нужен Redis, хорошо масштабируется. Но нельзя отозвать токен до истечения TTL. Украденный токен работает до expire — это неприемлемо.

**Opaque tokens (сессии целиком в Redis)** — полный контроль. Но каждый запрос идёт в Redis за данными пользователя, нет стандартного формата, всё самописное.

**JWT + Redis whitelist/blacklist** — выбрал этот. JWT самодостаточен (роль уже внутри, лишний запрос в БД не нужен), при этом токен можно отозвать в любой момент через чёрный список. Redis хранит только лёгкие строковые ключи, не полные данные сессии. Единственный минус — зависимость от Redis, но это решается репликацией.

---

## Безопасность и утечки токенов

### Как токен может утечь

- XSS — если токен в localStorage, вредоносный JS его прочитает
- MITM — перехват по незашифрованному каналу
- Утечка логов — токен попал в логи сервера в открытом виде
- Компрометация клиента — вирус, keylogger

### Как обнаружить кражу

В проекте реализовано вытеснение сессии: один пользователь = один активный токен. Если легитимный пользователь логинится заново, старый токен отзывается. Если атакующий каким-то образом делает новый логин с украденными данными — легитимный пользователь получит "token superseded" на следующем запросе.

Что ещё можно добавить (не реализовано):

- Fingerprinting — сохранять User-Agent и IP при выдаче токена, сравнивать при каждом запросе
- Refresh token rotation — короткий access + длинный refresh, при повторном использовании старого refresh — полный logout всех сессий
- Geo-velocity detection — логин из одной страны, запрос через минуту из другой

### Меры защиты

| угроза | что делать |
|--------|-----------|
| XSS | httpOnly cookie вместо localStorage |
| MITM | только HTTPS, HSTS |
| долгоживущий токен | короткий TTL + refresh |
| параллельные сессии | single-session whitelist (реализовано) |
| украденный токен | blacklist при logout и при повторном логине (реализовано) |
| утечка секрета | JWT_SECRET_KEY из env, не хардкодить |

---

## Структура проекта

```
run/
    main.py                       - точка входа
src/
    core/
        domain/models.py          - доменные модели (dataclass)
        repositories.py           - абстрактные репозитории
    application/
        dto/auth.py               - pydantic схемы
        mappers/user.py           - маппинг между слоями
        use_case/auth.py          - login, register, logout, dummylogin
    infrastructure/
        auth/jwt.py               - создание и декодирование токенов
        cache/redis_client.py     - клиент redis
        database/                 - sqlalchemy, модели, репозитории
    interfaces/
        api/
            auth.py               - роуты авторизации
            content.py            - роуты контента
            dependencies.py       - get_current_user, require_role
    config/settings.py            - настройки через pydantic-settings
    migrations/                   - alembic
Dockerfile
docker-compose.yml
pyproject.toml
.env.example
```

## Что не реализовано

- Refresh-токены. При истечении access-токена нужен повторный логин. В продакшне это нужно добавить.
- Multi-device сессии. Сейчас один пользователь = одна сессия. Для нескольких устройств нужен ключ вида `whitelist:users:{user_id}:{device_id}`.
- Тесты. Зависимости подключены, сами тесты не написаны.
- Контент. Сейчас в место контента стоят заглушки.