FROM python:3.10
WORKDIR /app
COPY . /app/
RUN pip install --no-cache-dir -r requirements.txt
# Install ffmpeg and fonts
RUN apt update && apt install -y ffmpeg fonts-dejavu-core wget && \
    apt clean && rm -rf /var/lib/apt/lists/*
# Download ZURAMBI font
RUN mkdir -p helper && \
    cd helper && \
    wget https://www.1001fonts.com/download/font/zurambi.regular.ttf -O ZURAMBI.ttf || true
CMD ["python3", "bot.py"]
