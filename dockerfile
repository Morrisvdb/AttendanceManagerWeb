FROM python:3.13.9-alpine

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

ENV FLASK_APP=main.app

CMD ["flask", "run", "--host", "0.0.0.0", "--port", "5002"]

EXPOSE 5002