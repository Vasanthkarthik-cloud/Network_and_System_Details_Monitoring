FROM python:3.9-slim

# Create and set working directory
RUN mkdir -p /app
WORKDIR /app

# Copy requirements first
COPY ./app/requirements.txt /app/

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application
COPY ./app /app/

# Make sure the directory has correct permissions
RUN chmod -R 755 /app

EXPOSE 8501

CMD ["streamlit", "run", "Home.py"]