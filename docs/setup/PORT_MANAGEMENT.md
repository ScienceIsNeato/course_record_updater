# Port Management Strategy

## Overview

This document outlines the port allocation strategy to avoid conflicts between multiple applications running on your development machine.

## Port Allocation

### Reserved Ports

- **Port 5000**: macOS ControlCenter (system reserved)
- **Port 8080**: FogOfDog application
- **Port 3000**: Common React/Node.js applications

### LoopCloser Ports

- **Port 3001**: Default port for LoopCloser
- **Port 3002-3004**: Fallback ports if 3001 is occupied

## Starting the Server

### Method 1: Restart Server (Production Mode)

```bash
# Start with automatic port detection and environment setup
./restart_server.sh
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
   ./restart_server.sh
   ```

## Application URLs

Once started, access the applications at:

- **LoopCloser**: http://localhost:3001 (or your chosen port)
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

# Terminal 2: Start LoopCloser (port 3001)
cd /path/to/course_record_updater
./restart_server.sh

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

---

## Two-Environment Configuration

### Environment Variables

- `LOOPCLOSER_DEFAULT_PORT_DEV="3001"` - Development server port
- `LOOPCLOSER_DEFAULT_PORT_E2E="3002"` - E2E test server port (local & CI)

### Configuration Files

- **`.envrc.template`**: Template with port defaults
- **`.envrc`**: Local file (gitignored) that sources template

### Script Behavior

| Script                  | Environment | Port |
| ----------------------- | ----------- | ---- |
| `restart_server.sh dev` | Development | 3001 |
| `restart_server.sh e2e` | E2E Testing | 3002 |
| `run_uat.sh`            | E2E Testing | 3002 |

### Design Principles

1. **Two Environments Only**: dev (3001) and e2e (3002)
2. **Single Source of Truth**: Bash uses env vars, Python uses `constants.py`
3. **Environment-Aware**: Port determined by environment flag
4. **Fallback Defaults**: Scripts work even if env vars not set
