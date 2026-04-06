composite services, wrapper services, etc
## 🚀 Quick Start

### 1. Prerequisites
* **Docker (preferrably) & Docker Desktop** installed.

### 2. Environment Setup
The service requires specific environment variables to connect the components. Navigate to the each directory and create your `.env` file based on the `.env.example`:

Arrival Alert Composite Service:
```bash
# Navigate to the correct directory (from root)
cd arrival-alert-composite/

# Copy the example environment file
cp .env.example .env
```
Merchant Management Composite Service:
```bash
# Navigate to the correct directory (from root)
cd merchant-management-composite/

# Copy the example environment file
cp .env.example .env
```
Notification RabbitMQ Wrapper:
```bash
# Navigate to the correct directory (from root)
cd notification-rabbitmq-wrapper/

# Copy the example environment file
cp .env.example .env
```

> **Note:** This tutorial assumes that you are using an external AMQP service, such as cloudamqp

### 3. Launch with Docker
From the **main `/` folder**, run:

```bash
docker compose up -d --build
```

---
##  Service Architecture

| Service | External (Host) Port | Endpoint |
| :--- | :--- | :--- |
| **Arrival Alert Composite Service**  | **6767** | `http://<host>:6767` |
| **Merchant Management Composite Service**  | **6768** | `http://<host>:6768` |
| **Publisher API**  | **6700** | `http://<host>:6700` |