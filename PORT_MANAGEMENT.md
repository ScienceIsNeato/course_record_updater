# Port Management Strategy

## Overview

This document outlines the port allocation strategy to avoid conflicts between multiple applications running on your development machine.

## Port Allocation

### Reserved Ports
- **Port 5000**: macOS ControlCenter (system reserved)
- **Port 8080**: FogOfDog application
- **Port 3000**: Common React/Node.js applications

### Course Record Updater Ports
- **Port 3001**: Default port for Course Record Updater
- **Port 3002-3004**: Fallback ports if 3001 is occupied
- **Port 8086**: Firestore emulator
- **Port 4000**: Firestore emulator UI (optional)

## Starting the Server

### Method 1: Full Setup with Database (Recommended)
```bash
# Start both Firestore emulator and Flask app
./start_with_db.sh

# Start on a specific port
./start_with_db.sh 3005
```

### Method 2: Demo Mode (No Database)
```bash
# Start with automatic port detection
./start_server.sh --demo

# Start on a specific port
./start_server.sh --demo 3005
```

### Method 2: Direct Python Execution
```bash
# Default port (3001)
python app.py

# Custom port via environment variable
PORT=3005 python app.py
```

### Method 3: Flask CLI
```bash
# Set port via environment variable
export PORT=3001
flask run --host=0.0.0.0 --port=$PORT
```

## Port Conflict Resolution

If you encounter port conflicts:

1. **Check what's using the port:**
   ```bash
   lsof -i :3001
   ```

2. **Kill the conflicting process (if safe):**
   ```bash
   pkill -f "python app.py"
   ```

3. **Use an alternative port:**
   ```bash
   ./start_server.sh 3005
   ```

## Application URLs

Once started, access the applications at:
- **Course Record Updater**: http://localhost:3001 (or your chosen port)
- **FogOfDog**: http://localhost:8080
- **Other React apps**: http://localhost:3000

## Environment Variables

- `PORT`: Override the default port (3001)
- `FLASK_DEBUG`: Enable debug mode (`true`/`false`)
- `FLASK_ENV`: Set environment (`development`/`production`)

## Example Workflow

```bash
# Terminal 1: Start FogOfDog (port 8080)
cd /path/to/fogofdog
npm start  # or whatever starts FogOfDog

# Terminal 2: Start Course Record Updater (port 3001)
cd /path/to/course_record_updater
./start_server.sh

# Both applications now run without conflicts!
```

## Troubleshooting

### "Address already in use" Error
- The port is occupied by another process
- Use the startup script for automatic port detection
- Or manually specify a different port

### Can't Connect to Application
- Check if the server started successfully
- Verify the correct port in your browser URL
- Check firewall settings if accessing from another machine
