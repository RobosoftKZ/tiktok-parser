FROM python:3.11

WORKDIR /app

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt && python -m playwright install

COPY . .

CMD ["python", "main.py"]
