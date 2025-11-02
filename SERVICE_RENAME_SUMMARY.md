# Service Rename: api-mvp → searchsvc

**Date:** 2025-01-26  
**Status:** ✅ COMPLETED AND VERIFIED

---

## 🎯 Objective

Rename the service folder from `api-mvp` to `searchsvc` for clearer, more descriptive naming that better represents the service's purpose.

---

## 📝 Changes Made

### 1. ✅ Physical Folder Rename
```powershell
Move-Item -Path "services/api-mvp" -Destination "services/searchsvc"
```

### 2. ✅ Docker Compose Updates
**File:** `docker-compose.yaml`

- Updated API service dockerfile path: `services/api-mvp/Dockerfile` → `services/searchsvc/Dockerfile`
- Updated UI service dockerfile path: `services/api-mvp/tools/Dockerfile` → `services/searchsvc/tools/Dockerfile`

### 3. ✅ Main API Dockerfile Updates
**File:** `services/searchsvc/Dockerfile`

- Updated: `COPY services/api-mvp/requirements.txt ./` → `COPY services/searchsvc/requirements.txt ./`
- Updated: `COPY services/api-mvp /app` → `COPY services/searchsvc /app`

### 4. ✅ UI Dockerfile Updates
**File:** `services/searchsvc/tools/Dockerfile`

- Updated: `COPY services/api-mvp/tools/requirements.txt ./` → `COPY services/searchsvc/tools/requirements.txt ./`
- Updated: `COPY services/api-mvp/tools /app/tools` → `COPY services/searchsvc/tools /app/tools`

### 5. ✅ Documentation Updates

#### README.md
- Updated folder structure diagram
- Updated development section paths

#### services/searchsvc/tools/README.md
- Updated pip install path
- Updated streamlit run command

#### OPTIMIZATIONS_SUMMARY.md
- Updated all file references (6 locations)
- Updated verification commands (2 locations)
- Updated Redis configuration note

---

## 🔍 Verification

### Build Test
```powershell
docker compose build
```
✅ Result: Both `api` and `ui` services built successfully with new paths

### Service Start Test
```powershell
docker compose up -d
```
✅ Result: All 4 services started successfully:
- ✅ redis
- ✅ searxng
- ✅ api (searchsvc)
- ✅ ui (searchsvc/tools)

### API Health Check
```powershell
curl http://localhost:3000/
```
✅ Result: `{"status":"ok"}`

---

## 📁 Final Structure

```
simple_perplexica/
├── services/
│   └── searchsvc/              # ← Renamed from api-mvp
│       ├── app/
│       │   ├── main.py
│       │   ├── models.py
│       │   ├── providers/
│       │   ├── search_clients/
│       │   ├── routers/
│       │   └── utils/
│       ├── tools/
│       │   ├── streamlit_app.py
│       │   ├── requirements.txt
│       │   ├── Dockerfile
│       │   └── README.md
│       ├── Dockerfile
│       └── requirements.txt
├── searxng/
├── docker-compose.yaml
└── README.md
```

---

## 🚀 Active Services

All services running on the same ports as before:

- **Search API:** http://localhost:3000
- **SearxNG:** http://localhost:8080
- **Redis:** localhost:6379 (internal)
- **Streamlit UI:** http://localhost:8501

---

## 📋 Files Modified

### Configuration Files
1. `docker-compose.yaml` - 2 dockerfile path updates
2. `services/searchsvc/Dockerfile` - 2 COPY path updates
3. `services/searchsvc/tools/Dockerfile` - 2 COPY path updates

### Documentation Files
4. `README.md` - Updated structure diagram and dev commands
5. `services/searchsvc/tools/README.md` - Updated pip and streamlit commands
6. `OPTIMIZATIONS_SUMMARY.md` - Updated all file references and commands

### Historical Documentation
- `specs/` folder - Intentionally left unchanged (historical accuracy)

---

## ✅ Summary

The service folder has been successfully renamed from `api-mvp` to `searchsvc` with:
- ✅ Physical folder moved
- ✅ All Docker build paths updated
- ✅ All documentation references updated
- ✅ Containers rebuilt successfully
- ✅ All services verified running
- ✅ API health check passed

The rename is complete and the system is fully operational with the new naming convention.
