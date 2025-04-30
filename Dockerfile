# Base image
FROM python:3.10-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libaio1 \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# Install Oracle Instant Client (basiclite)
RUN mkdir -p /opt/oracle && \
    cd /opt/oracle && \
    curl -O https://download.oracle.com/otn_software/linux/instantclient/instantclient-basiclite-linux.x64-21.12.0.0.0dbru.zip && \
    unzip instantclient-basiclite-linux.x64-21.12.0.0.0dbru.zip && \
    rm instantclient-basiclite-linux.x64-21.12.0.0.0dbru.zip

ENV LD_LIBRARY_PATH=/opt/oracle/instantclient_21_12

# Set working directory
WORKDIR /app

# Copy app files
COPY . .

# Install Python dependencies
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Expose port
EXPOSE 8501

# Run the Streamlit app
CMD ["streamlit", "run", "1_📊_Override_Report.py", "--server.port=8501", "--server.address=0.0.0.0"]
