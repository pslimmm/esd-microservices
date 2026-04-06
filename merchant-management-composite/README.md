# Merchant Management Composite Service

This repository contains a Flask-based API. Below are the instructions to get the application up and running using either a local Python environment or Docker Compose.

---

## Local Setup

Follow these steps to configure the project on your local machine.

### 1. Environment Preparation
First, create a virtual environment to isolate your dependencies and activate it:

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

**macOS/Linux:**
```bash
python -m venv venv
source venv/bin/activate
```

### 2. Install Dependencies
Ensure you have `pip` updated, then install the required packages:
```bash
pip install -r requirements.txt
```

### 3. Configuration
Create a `.env` file based on the `.env.example` in the `/arrival-alert-composite` directory and populate it with the necessary environment variables:

### 4. Running the Application
Start the Flask development server:
```bash
flask run
```
Once the server is running, you can access the API documentation at:
**`http://127.0.0.1:5000/apidocs`**
or 
**`http://127.0.0.1:5001/apidocs`**
if you happen to have another Flask API running

---

## Docker Compose Setup

Use Docker for a streamlined, containerized environment.

### 1. Configuration
Ensure your `.env` file is present in the root directory, as Docker Compose will use these variables to configure the container. Use the `.env.example` to generate this file.

### 2. Build and Launch
Run the following command to build the images and start the services in detached mode:
```bash
docker compose up -d --build
```

### 3. Accessing the API
The application will be mapped to your host machine. You can view the Swagger/OpenAPI documentation at:
**`http://localhost:6768/apidocs`**

### 4. Stopping the Container
To stop the services, run:
```bash
docker compose down
```