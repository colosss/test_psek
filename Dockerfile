FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

RUN pip install poetry

WORKDIR /app

COPY poetry.lock pyproject.toml ./
RUN poetry config virtualenvs.create false && poetry install --no-root --without dev

COPY . .

CMD ["poetry", "run", "uvicorn", "run.main:app", "--host", "0.0.0.0", "--port", "8000"]