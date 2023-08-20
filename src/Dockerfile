FROM python:3.11-slim-bookworm

COPY ./app /app
WORKDIR /app

RUN pip install pipenv

RUN pipenv install --system --deploy

CMD ["python", "main.py"]