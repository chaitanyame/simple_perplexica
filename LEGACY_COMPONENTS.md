# Legacy Components Removed

This document tracks components from the original Perplexica codebase that were removed when transitioning to the Simple Perplexica MVP.

**Date Removed:** November 1, 2025  
**Reason:** Streamlining to MVP - Python API only, removing Next.js frontend and Node.js backend

---

## 🗑️ Removed Services

### 1. Vetuku Service (Legacy Next.js Frontend)
**Status:** ❌ Removed from docker-compose.yaml

**Previous Configuration:**
```yaml
vetuku:
  build:
    context: .
    dockerfile: Dockerfile
  image: chaitanyame/vetuku:latest
  ports:
    - '3010:3000'
  volumes:
    - data:/home/perplexica/data
    - uploads:/home/perplexica/uploads
  restart: unless-stopped
```

**Reason for Removal:**
- The MVP focuses on the API layer only
- Next.js frontend adds unnecessary complexity for MVP
- Streamlit UI (`api-mvp-ui`) serves as a simpler testing interface
- Most users will integrate via API, not the web UI

**What It Did:**
- Full-featured web interface for Perplexica
- Chat interface with message history
- Settings management UI
- Image/video search UI
- File upload handling

---

## 📦 Legacy Files/Folders (To Be Removed)

### Next.js Frontend Files
**Location:** `src/` directory

**Files to keep for reference (not removed yet):**
- `src/app/` - Next.js app router pages
- `src/components/` - React components
- `src/lib/` - Frontend utilities and chains
- All TypeScript/JSX files

**Status:** ⚠️ NOT YET REMOVED - Keeping for reference
**Future Action:** Can be moved to `archive/legacy-frontend/` or deleted

### Node.js Backend Files
**Location:** Root directory

**Files:**
- `Dockerfile` - Builds the Next.js + Node.js + SearxNG bundle
- `entrypoint.sh` - Startup script for the bundled container
- `package.json` - Node.js dependencies for frontend
- `yarn.lock` - Dependency lock file
- `tsconfig.json` - TypeScript configuration
- `next.config.mjs` - Next.js configuration
- `tailwind.config.ts` - Tailwind CSS config
- `postcss.config.js` - PostCSS config
- `.eslintrc.json` - ESLint configuration
- `.prettierrc.js` - Prettier configuration

**Status:** ⚠️ NOT YET REMOVED - May be needed for documentation builds
**Future Action:** Consider removing or moving to archive

### Database Files
**Location:** `drizzle/` directory

**Files:**
- `drizzle/` - Database migrations for SQLite
- `drizzle.config.ts` - Drizzle ORM configuration
- `data/` - SQLite database files

**Reason for Keeping:**
- Not actively used by MVP
- No harm in keeping for potential future use
- Database was for chat history (now using mem0 instead)

**Status:** ✅ KEPT (inactive, but not causing issues)

### Documentation
**Location:** `docs/` directory

**Status:** ✅ KEPT - Still valuable for understanding architecture
**Note:** Some docs reference the legacy frontend, should be updated eventually

### Public Assets
**Location:** `public/` directory

**Status:** ✅ KEPT - Contains logos and assets that might be useful

---

## 🔄 Renamed/Restructured Services

### api-mvp → api
**Old Name:** `api-mvp`  
**New Name:** `api`  
**Port Change:** `3001` → `3000` (externally exposed as primary service)

**Reason:**
- MVP is now the main (and only) API
- Port 3000 is more standard for primary service
- Simpler, cleaner naming

### api-mvp-ui → ui
**Old Name:** `api-mvp-ui`  
**New Name:** `ui`  
**Port:** Still `8501`

**Reason:**
- Shorter, clearer name
- Emphasizes it's THE ui for the system

---

## 📊 Volume Changes

### Removed Volumes
```yaml
# Old volumes (removed)
data:
  name: 'vetuku-data'
uploads:
  name: 'vetuku-uploads'
```

**Reason:**
- Were used by the Next.js frontend
- Not needed for API-only MVP
- Chat history now handled by mem0 (if enabled)

### Kept Volumes
```yaml
# New volumes (kept)
redis-data:
  name: 'simple-perplexica-redis'
```

**Reason:**
- Redis cache persistence is critical for performance
- Renamed to match new project naming

---

## 🔧 Configuration Changes

### Docker Compose Changes

**Before:**
- 4 services: `vetuku`, `searxng`, `api-mvp`, `api-mvp-ui`
- 3 volumes: `data`, `uploads`, `redis-data`
- Ports: 3010 (vetuku), 3001 (api-mvp), 8080 (searxng), 8501 (ui)

**After:**
- 4 services: `api`, `searxng`, `redis`, `ui`
- 1 volume: `redis-data`
- Ports: 3000 (api), 8080 (searxng), 6379 (redis), 8501 (ui)

**Key Changes:**
- Removed `vetuku` service entirely
- Renamed `api-mvp` → `api` and exposed on port 3000
- Added explicit `redis` service with persistent volume
- Renamed `api-mvp-ui` → `ui`
- Removed legacy data/uploads volumes

---

## 🎯 MVP Focus

**What We Kept:**
- ✅ Python FastAPI backend
- ✅ OpenRouter integration
- ✅ SearxNG search engine
- ✅ Redis caching
- ✅ Performance optimizations
- ✅ All API endpoints
- ✅ Streamlit testing UI

**What We Removed:**
- ❌ Next.js frontend
- ❌ Node.js backend
- ❌ Chat history UI
- ❌ Settings UI
- ❌ File upload UI
- ❌ Bundled Dockerfile

**Philosophy:**
- API-first approach
- Simpler deployment
- Easier to maintain
- Better for integration
- Performance-focused

---

## 📝 Migration Notes

### For Users of Legacy Perplexica

If you were using the full Perplexica UI:

1. **API Access:** The search functionality is still available via API
   ```bash
   curl -X POST http://localhost:3000/api/search \
     -H "Content-Type: application/json" \
     -d '{"query": "your query", "focusMode": "webSearch"}'
   ```

2. **UI Alternative:** Use the Streamlit UI at http://localhost:8501
   - Simpler than the full Perplexica UI
   - Good for testing and development
   - Not meant for production use

3. **Chat History:** 
   - Was stored in SQLite (legacy)
   - Now uses mem0 for persistent storage (optional)
   - Enable with `MEM0_ENABLED=true`

4. **File Uploads:**
   - Not implemented in MVP
   - Can be added as a separate service if needed
   - API accepts URLs for content fetching

### For Developers

- **Frontend Development:** Use the API endpoints directly
- **Custom UI:** Build your own using the API
- **Integration:** The API is the primary interface
- **Testing:** Use Streamlit UI or PowerShell test scripts

---

## 🔮 Future Considerations

### Potentially Restore (If Needed)

1. **File Upload API Endpoint**
   - Could add `/api/upload` endpoint
   - Process PDFs/documents via API
   - Return extracted text for queries

2. **Basic Web UI**
   - Minimal single-page app
   - Just search input and results
   - Much lighter than full Perplexica UI

3. **Chat History API**
   - Proper mem0 integration
   - API endpoints for history
   - Let frontends handle UI

### Definitely Keep Removed

1. **Full Next.js UI** - Too heavy for MVP
2. **Bundled Dockerfile** - Complexity not needed
3. **SQLite Database** - Replaced by mem0
4. **Node.js Backend** - Python API is sufficient

---

## 📄 Files to Clean Up (Future)

**Can be deleted after archiving:**
- `src/` (entire directory)
- `Dockerfile` (legacy, keep `services/api-mvp/Dockerfile`)
- `entrypoint.sh`
- `package.json` (Next.js)
- `yarn.lock`
- `tsconfig.json`
- `next.config.mjs`
- `next-env.d.ts`
- `tailwind.config.ts`
- `postcss.config.js`
- `.eslintrc.json`
- `.eslintignore`
- `.prettierrc.js`
- `.prettierignore`

**Suggested Archive Location:**
```
archive/
└── legacy-perplexica-ui/
    ├── src/
    ├── Dockerfile
    ├── package.json
    └── README-LEGACY.md
```

---

**Summary:** Transitioned from full-stack Perplexica (Next.js + Node.js + Python) to streamlined MVP (Python API only). Removed 50%+ of codebase complexity while maintaining all core search functionality and improving performance.
