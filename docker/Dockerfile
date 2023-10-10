FROM python:3-alpine

WORKDIR /app
COPY ./src/. ./
RUN pip install --no-cache-dir --upgrade -r ./requirements.txt

EXPOSE 5000

CMD [ "uvicorn", "app:app","--host","0.0.0.0","--port","5000"]
