# Starlink Manager - Docker Quick Start

This guide provides quick instructions for running Starlink Manager with Docker.

## Quick Start (Local Development)

### 1. Prerequisites

- Docker installed
- Docker Compose installed

### 2. Clone and Setup

```bash
git clone https://github.com/dadishimwe/cuddly-invention.git starlink-manager
cd starlink-manager
cp .env.example .env
```

### 3. Configure Environment

Edit `.env` and add your credentials:

```env
STARLINK_CLIENT_ID=your_client_id
STARLINK_CLIENT_SECRET=your_client_secret
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_app_password
FLASK_SECRET_KEY=generate_random_key_here
```

### 4. Build and Run

```bash
docker-compose build
docker-compose up -d
```

### 5. Access Application

- Admin Dashboard: http://localhost:5000
- Health Check: http://localhost:5000/health

### 6. View Logs

```bash
docker-compose logs -f
```

### 7. Stop Application

```bash
docker-compose down
```

## Production Deployment

For production deployment on a VPS, see [DEPLOYMENT_VPS.md](DEPLOYMENT_VPS.md)

## Docker Commands Reference

### Build

```bash
# Build image
docker-compose build

# Build without cache
docker-compose build --no-cache
```

### Run

```bash
# Start in background
docker-compose up -d

# Start with logs
docker-compose up

# Restart
docker-compose restart
```

### Logs

```bash
# View all logs
docker-compose logs

# Follow logs
docker-compose logs -f

# Last 100 lines
docker-compose logs --tail=100
```

### Shell Access

```bash
# Access container shell
docker-compose exec starlink-manager bash

# Run Python script
docker-compose exec starlink-manager python3 /app/scripts/manage.py list-mappings
```

### Database Management

```bash
# Initialize database
docker-compose exec starlink-manager python3 /app/scripts/manage.py init --v2

# Import clients from CSV
docker-compose exec starlink-manager python3 /app/scripts/import_csv_improved.py /app/config/clients_import.csv

# Backup database
docker-compose exec starlink-manager cp /app/data/starlink_manager.db /app/data/backup_$(date +%Y%m%d).db
```

### Cleanup

```bash
# Stop and remove containers
docker-compose down

# Remove volumes (WARNING: deletes data)
docker-compose down -v

# Remove images
docker-compose down --rmi all
```

## Volume Management

Data is persisted in the following directories:

- `./data` - SQLite database
- `./logs` - Application logs
- `./config` - Configuration files and CSV imports

## Health Checks

The container includes health checks that run every 30 seconds:

```bash
# Check container health
docker inspect starlink-manager | grep -A 10 Health

# Manual health check
curl http://localhost:5000/health
```

## Troubleshooting

### Container won't start

```bash
# Check logs
docker-compose logs

# Check if port is in use
sudo lsof -i :5000
```

### Database errors

```bash
# Reinitialize database (WARNING: deletes data)
docker-compose exec starlink-manager python3 /app/scripts/manage.py init --v2
```

### Permission errors

```bash
# Fix permissions
sudo chown -R $USER:$USER data/ logs/
```

## Environment Variables

See `.env.example` for all available configuration options.

## Support

For detailed VPS deployment instructions, see [DEPLOYMENT_VPS.md](DEPLOYMENT_VPS.md)
