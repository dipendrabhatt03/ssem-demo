# SSEM Demo - Full Stack Notes Application

A simple full-stack application demonstrating end-to-end flow for Harness IDP. This application includes:
- **Backend**: Python FastAPI REST API
- **Frontend**: Vanilla JavaScript, HTML, CSS
- **Database**: PostgreSQL

## Architecture

```
Frontend (index.html + app.js)
    ↓ HTTP Requests
Backend (FastAPI - Python)
    ↓ SQL Queries
Database (PostgreSQL)
```

## Features

- Create, read, and delete notes
- Real-time connection status
- RESTful API design
- Responsive UI
- Full CRUD operations

## Prerequisites

**Option 1: Docker (Recommended)**
- Docker and Docker Compose

**Option 2: Local Development**
- Python 3.8+
- Docker and Docker Compose (for PostgreSQL)
- A web browser

## Project Structure

```
ssem-demo/
├── backend/
│   ├── main.py              # FastAPI application
│   ├── requirements.txt     # Python dependencies
│   └── .env.example         # Environment variables example
├── frontend/
│   ├── index.html          # Main HTML file
│   ├── style.css           # Styles
│   └── app.js              # Frontend JavaScript
├── Dockerfile              # Container image for backend + frontend
├── docker-compose.yml      # Full stack deployment
└── README.md              # This file
```

## Quick Start with Docker (Recommended)

The easiest way to run the entire application is using Docker Compose:

```bash
# Build and start all services (database, backend, frontend)
docker-compose up --build

# Or run in detached mode
docker-compose up --build -d
```

This will start:
- PostgreSQL database on `localhost:5432`
- Backend API on `http://localhost:8000`
- Frontend on `http://localhost:3000`

Open `http://localhost:3000` in your browser to use the application!

To stop:
```bash
docker-compose down

# To also remove data
docker-compose down -v
```

## Local Development Setup (Without Docker)

### 1. Start PostgreSQL Database

```bash
# Start PostgreSQL using Docker Compose
docker-compose up -d postgres

# Verify it's running
docker ps
```

The database will be available at `localhost:5432` with:
- Database: `notesdb`
- User: `postgres`
- Password: `postgres`

### 2. Setup Backend

```bash
# Navigate to backend directory
cd backend

# Create virtual environment (optional but recommended)
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start the FastAPI server
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The backend API will be available at `http://localhost:8000`

You can view the auto-generated API documentation at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### 3. Setup Frontend

```bash
# Navigate to frontend directory (in a new terminal)
cd frontend

# Start a simple HTTP server
python3 -m http.server 3000
```

The frontend will be available at `http://localhost:3000`

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Root endpoint |
| GET | `/health` | Health check |
| GET | `/notes` | Get all notes |
| POST | `/notes` | Create a new note |
| GET | `/notes/{id}` | Get a specific note |
| PUT | `/notes/{id}` | Update a note |
| DELETE | `/notes/{id}` | Delete a note |

## Testing the Application

1. Open `http://localhost:3000` in your browser
2. You should see "Connected to backend and database" status
3. Create a new note by filling in the title and content
4. View all notes in the list below
5. Delete notes using the Delete button

## Development

### Backend Development

The FastAPI server runs with auto-reload enabled, so changes to `main.py` will automatically restart the server.

### Frontend Development

Simply refresh the browser to see changes to HTML, CSS, or JavaScript files.

### Database Management

Connect to PostgreSQL using any client:
```bash
# Using psql
docker exec -it ssem-demo-postgres psql -U postgres -d notesdb

# View tables
\dt

# View notes
SELECT * FROM notes;
```

## Stopping the Application

**If using Docker:**
```bash
# Stop all services
docker-compose down

# Stop and remove data
docker-compose down -v
```

**If running locally:**
```bash
# Stop backend (Ctrl+C in the terminal running uvicorn)

# Stop frontend (Ctrl+C in the terminal running http.server)

# Stop database
docker-compose down
```

## Environment Variables

The backend uses these environment variables (with defaults):

- `DB_HOST`: Database host (default: localhost)
- `DB_PORT`: Database port (default: 5432)
- `DB_NAME`: Database name (default: notesdb)
- `DB_USER`: Database user (default: postgres)
- `DB_PASSWORD`: Database password (default: postgres)

## Troubleshooting

### Backend won't start
- Check if PostgreSQL is running: `docker ps`
- Check if port 8000 is available
- Verify Python dependencies are installed

### Frontend can't connect to backend
- Verify backend is running at `http://localhost:8000`
- Check browser console for CORS errors
- Ensure API_URL in `app.js` matches your backend URL

### Database connection issues
- Verify PostgreSQL container is running
- Check database credentials
- Ensure port 5432 is not blocked

## Next Steps for Harness IDP

This application is ready to be integrated with Harness IDP:

1. **Catalog**: Register this service in the service catalog
2. **CI/CD**: Set up pipelines for automated deployment
3. **Templates**: Create scaffolding templates based on this structure
4. **Monitoring**: Add health checks and metrics
5. **Documentation**: Import this README into the portal

## License

This is a demo application for learning purposes.
