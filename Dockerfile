FROM python:3.11-slim

WORKDIR /app

# System dependencies for unzip and potential Oracle deps
RUN apt-get update && \
    apt-get install -y unzip build-essential libaio-dev libnsl2 -y && \
    apt-get clean

# Create the /opt/oracle/lib directory
RUN mkdir -p /opt/oracle/lib

# Copy the Oracle Instant Client ZIP file (full basic version)
COPY oracle/instantclient-basic-linux.x64-21.12.0.0.0dbru.el9.zip .

# Unzip the Instant Client
RUN unzip instantclient-basic-linux.x64-21.12.0.0.0dbru.el9.zip -d /opt/oracle/temp_instantclient

# Move the .so files to /opt/oracle/lib
RUN find /opt/oracle/temp_instantclient -name "*.so*" -exec mv {} /opt/oracle/lib \;

# Create symbolic links for libclntsh.so (common older versions)
RUN cd /opt/oracle/lib && \
    if [ -f libclntsh.so.21.1 ]; then \
        ln -sf libclntsh.so.21.1 libclntsh.so; \
        ln -sf libclntsh.so.21.1 libclntsh.so.11.1; \
        ln -sf libclntsh.so.21.1 libclntsh.so.12.1; \
        ln -sf libclntsh.so.21.1 libclntsh.so.18.1; \
        ln -sf libclntsh.so.21.1 libclntsh.so.19.1; \
        ln -sf libclntsh.so.21.1 libclntsh.so.20.1; \
    fi

# Remove the temporary directory and the zip file
RUN rm -rf /opt/oracle/temp_instantclient instantclient-basic-linux.x64-21.12.0.0.0dbru.el9.zip

# Set LD_LIBRARY_PATH
ENV LD_LIBRARY_PATH=/opt/oracle/lib:$LD_LIBRARY_PATH
ENV PATH="/opt/oracle:$PATH"

COPY . .

RUN pip install --upgrade pip
RUN pip install -r requirements.txt

EXPOSE 8501

CMD ["streamlit", "run", "Home.py", "--server.port=8501", "--server.address=0.0.0.0"]