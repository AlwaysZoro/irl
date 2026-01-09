FROM python:3.10
WORKDIR /app
COPY . /app/
RUN pip install -r requirements.txt
# Install ffmpeg and fonts
RUN apt update && apt install -y ffmpeg fonts-dejavu-core wget unzip
# Download ZURAMBI font
RUN mkdir -p /usr/share/fonts/truetype/custom && \
    cd /tmp && \
    wget https://www.1001fonts.com/download/font/zurambi.regular.ttf -O /usr/share/fonts/truetype/custom/zurambi.ttf || true
CMD ["python3", "bot.py"]
