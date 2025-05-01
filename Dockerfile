FROM python:3.11-slim

WORKDIR /app

# System dependencies for unzip
RUN apt-get update && \
    apt-get install -y unzip build-essential libaio-dev -y && \
    apt-get clean

# Copy the Oracle Instant Client ZIP file from the 'oracle' directory in the build context
COPY oracle/instantclient-basiclite-linux.x64-21.12.0.0.0dbru.el9.zip .

# Unzip and move the Instant Client
RUN unzip instantclient-basiclite-linux.x64-21.12.0.0.0dbru.el9.zip && \
    mv instantclient_21_12 /opt/oracle && \
    rm instantclient-basiclite-linux.x64-21.12.0.0.0dbru.el9.zip

# Set LD_LIBRARY_PATH so the system can find the Oracle Client libraries
ENV LD_LIBRARY_PATH=/opt/oracle/lib:$LD_LIBRARY_PATH
ENV PATH="/opt/oracle:$PATH"

COPY . .

RUN pip install --upgrade pip
RUN pip install -r requirements.txt

EXPOSE 8501

CMD ["streamlit", "run", "Home.py", "--server.port=8501", "--server.address=0.0.0.0"]