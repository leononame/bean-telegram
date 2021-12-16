FROM python:3.7 as builder

WORKDIR /app
COPY requirements.txt requirements.txt
RUN pip wheel -w /wheels -r requirements.txt


FROM python:3-slim as runner
COPY --from=builder /wheels /wheels

WORKDIR /app
COPY . /app
RUN pip install --no-index --find-links=/wheels -r requirements.txt 
RUN rm -rf /wheel
CMD ["python", "main.py"]
