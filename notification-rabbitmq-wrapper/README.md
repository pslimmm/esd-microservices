# Notification RabbitMQ Wrapper Service

A Node.js microservice wrapper that handles message brokering via RabbitMQ. This service includes a **Publisher** (API) and a **Consumer** (Worker) to manage notification flows.

## 🚀 Quick Start

### 1. Prerequisites
* **Docker & Docker Desktop** installed.
* **Node.js v20+** (if running locally without Docker).

### 2. Environment Setup
The service requires specific environment variables to connect the components. Navigate to the wrapper directory and create your `.env` file:

```bash
# Navigate to the correct directory
cd notification-alert-wrapper/

# Copy the example environment file
cp .env.example .env
```

> **Note:** This tutorial assumes that you are using an external AMQP service, such as cloudamqp

### 3. Launch with Docker
From the **main `rabbitmq-wrapper` folder**, run:

```bash
docker compose up -d --build
```

---

##  Service Architecture

| Service | External (Host) Port | Endpoint |
| :--- | :--- | :--- |
| **Publisher API**  | **6700** | `http://localhost:6700` |



