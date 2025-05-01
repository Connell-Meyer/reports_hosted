FROM python:3.11-slim

WORKDIR /app

# System dependencies for Oracle + unzip + curl
RUN apt-get update && \
    apt-get install -y libaio1 unzip curl && \
    apt-get clean

# Install Oracle Instant Client Lite (small, Docker-safe)
RUN curl -O https://download.oracle.com/otn_software/linux/instantclient/211000/instantclient-basiclite-linux.x64-21.10.0.0.0dbru.zip && \
    unzip instantclient-basiclite-linux.x64-21.10.0.0.0dbru.zip && \
    mv instantclient_21_10 /opt/oracle && \
    rm instantclient-basiclite-linux.x64-21.10.0.0.0dbru.zip

ENV LD_LIBRARY_PATH=/opt/oracle
ENV PATH="/opt/oracle:$PATH"

COPY . .

RUN pip install --upgrade pip
RUN pip install -r requirements.txt

EXPOSE 8501

CMD ["streamlit", "run", "Home.py", "--server.port=8501", "--server.address=0.0.0.0"]
