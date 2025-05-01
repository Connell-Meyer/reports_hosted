FROM python:3.11-slim

WORKDIR /app

# System dependencies for Oracle + unzip + curl
RUN apt-get update && \
    apt-get install -y libaio1 unzip curl && \
    apt-get clean

# Attempt to download Oracle Instant Client Lite with retries
RUN set -ex; \
    attempt=1; \
    max_attempts=3; \
    while [ "$attempt" -le "$max_attempts" ]; do \
        curl -o instantclient-basiclite-linux.x64-21.10.0.0.0dbru.zip https://download.oracle.com/otn_software/linux/instantclient/211000/instantclient-basiclite-linux.x64-21.10.0.0.0dbru.zip -H 'Cookie: oraclelicense=accept-securebackup-cookie' && break; \
        echo "Download failed. Attempt $attempt of $max_attempts..."; \
        sleep $((2 ** attempt)); \
        attempt=$((attempt + 1)); \
    done; \
    if [ "$attempt" -gt "$max_attempts" ]; then \
        echo "Failed to download Oracle Instant Client after $max_attempts attempts." && exit 1; \
    fi && \
    unzip instantclient-basiclite-linux.x64-21.10.0.0.0dbru.zip && \
    mv instantclient_21_10 /opt/oracle && \
    rm instantclient-basiclite-linux.x64-21.10.0.0.0dbru.zip

ENV LD_LIBRARY_PATH=/opt/oracle/lib
ENV PATH="/opt/oracle:$PATH"

COPY . .

RUN pip install --upgrade pip
RUN pip install -r requirements.txt

EXPOSE 8501

CMD ["streamlit", "run", "Home.py", "--server.port=8501", "--server.address=0.0.0.0"]