FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN mkdir -p data
EXPOSE 8050
CMD ["sh", "-c", "python -u src/setup_data.py && python -u src/dashboard.py"]