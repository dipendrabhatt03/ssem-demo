FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy backend code
COPY backend/ /app/backend/

# Copy frontend code
COPY frontend/ /app/frontend/

# Install Python dependencies
RUN pip install --no-cache-dir -r backend/requirements.txt

# Expose ports
# 8000 for backend API
# 3000 for frontend
EXPOSE 8000 3000

# Default command runs the backend
# To run frontend, use: python3 -m http.server 3000 --directory /app/frontend
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
