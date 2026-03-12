FROM python:3.11-slim

WORKDIR /app
COPY . /app

# Install system dependencies (Debian uses apt-get)
RUN apt-get update && apt-get install -y \
    gcc \
    build-essential \
    librdkafka-dev \
    libffi-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Install internal libraries
RUN pip install --no-cache-dir \
https://general-iamdave-mumbai.s3.ap-south-1.amazonaws.com/dave-python-libs/ai_service/ai_service-0.0.7-py3-none-any.whl \
https://general-iamdave-mumbai.s3.ap-south-1.amazonaws.com/dave-python-libs/gryd_worker/gryd_worker-0.5.0-py3-none-any.whl

# Install project dependencies
RUN pip install --no-cache-dir -r requirements.txt

#CMD ["python", "brochure_task.py"]
CMD ["worker", "-m", "brochure_task.py"]
