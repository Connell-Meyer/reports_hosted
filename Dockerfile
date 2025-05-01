FROM python:3.11-slim

WORKDIR /app

# System dependencies for unzip
RUN apt-get update && \
    apt-get install -y unzip build-essential libaio-dev -y && \
    apt-get clean

# Copy the Oracle Instant Client ZIP file
COPY oracle/instantclient-basiclite-linux.x64-21.12.0.0.0dbru.el9.zip .

# Unzip and move the Instant Client libraries
RUN unzip instantclient-basiclite-linux.x64-21.12.0.0.0dbru.el9.zip && \
    mv instantclient_21_12/* /opt/oracle/ && \
    rm -rf instantclient_21_12 instantclient-basiclite-linux.x64-21.12.0.0.0dbru.el9.zip

ENV LD_LIBRARY_PATH=/opt/oracle:$LD_LIBRARY_PATH
ENV PATH="/opt/oracle:$PATH"

COPY . .

RUN pip install --upgrade pip
RUN pip install -r requirements.txt

EXPOSE 8501

CMD ["streamlit", "run", "Home.py", "--server.port=8501", "--server.address=0.0.0.0"]