# Use official Playwright base with Python + modern GLIBC
FROM mcr.microsoft.com/playwright:v1.51.1-noble

# Set working directory
WORKDIR /app

# Copy project files
COPY . .

# Install pip and create a virtual environment
RUN apt-get update && apt-get install -y python3-pip python3-venv && rm -rf /var/lib/apt/lists/* \
    && python3 -m venv /app/venv \
    && /app/venv/bin/pip install --upgrade pip \
    && /app/venv/bin/pip install -r requirements.txt

# Install Playwright browsers
RUN /app/venv/bin/playwright install

# Set default command to run your app
CMD ["/app/venv/bin/python", "main.py"]
