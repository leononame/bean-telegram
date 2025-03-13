FROM python:3.13 AS builder

WORKDIR /app
COPY . /app
RUN pip install -U pip setuptools
RUN pip install poetry
RUN poetry install
CMD ["poetry", "run", "python", "main.py"]
