# Creating MediaVault Project in Langfuse

**Goal:** Create dedicated "mediavault" project in Langfuse for better organization

---

## Manual Setup (Web UI)

### Step 1: Login to Langfuse
1. Go to: https://langfuse.orourkes.me
2. Login with your credentials

### Step 2: Create New Project (Under "Minerva" Organization)
1. **Look for:** Settings icon (gear) or Project dropdown in top navigation
2. **Verify:** You're in the "Minerva" organization (same as Bimodal Agent)
3. **Click:** "New Project" or "Create Project" button
4. **Enter Details:**
   - **Organization:** Minerva (should be pre-selected)
   - **Name:** `mediavault` (or `MediaVault`)
   - **Description:** Media organization and deduplication system
5. **Click:** Create/Save

### Step 3: Get API Keys
1. Navigate to the new "mediavault" project
2. Go to **Settings** → **API Keys**
3. Copy both keys:
   - **Public Key:** `pk-lf-...` (starts with pk-lf)
   - **Secret Key:** `sk-lf-...` (starts with sk-lf)
4. Copy the **Project ID** (will be something like `cm...`)

### Step 4: Update MediaVault Configuration

**Add to `/home/mercury/projects/mediavault/.env`:**
```bash
# Langfuse MediaVault Project
LANGFUSE_PUBLIC_KEY=pk-lf-XXXXXXXXX  # Replace with new key
LANGFUSE_SECRET_KEY=sk-lf-XXXXXXXXX  # Replace with new key
LANGFUSE_HOST=http://10.27.10.104:3010
LANGFUSE_PROJECT_ID=cmXXXXXXXXXXXXX  # Replace with new project ID
```

---

## Alternative: Use Existing "Bimodal Agent" Project

If you prefer to keep everything in one project for now:

**Current Config (Bimodal Agent project):**
```bash
# From /home/mercury/projects/bimodal_agent/.env
LANGFUSE_PUBLIC_KEY=pk-lf-ab2d7168-4003-498b-874a-43ee4fc6207e
LANGFUSE_SECRET_KEY=sk-lf-dc1e9589-687f-43ed-945e-af9df0908a90
LANGFUSE_HOST=http://10.27.10.104:3010

# Project ID (from URL)
LANGFUSE_PROJECT_ID=cmhapoi2p00067fp318zwhsl4
```

**Pros:**
- All traces in one place
- Unified search across projects
- Can filter by tags: `project:mediavault`

**Cons:**
- Mixed traces from different apps
- Harder to analyze MediaVault-specific metrics

---

## Backend Configuration (When Built)

### Option 1: Dedicated MediaVault Project (Recommended)

**backend/app/config.py:**
```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Langfuse
    langfuse_public_key: str
    langfuse_secret_key: str
    langfuse_host: str = "http://10.27.10.104:3010"
    langfuse_project_id: str  # MediaVault project ID

    class Config:
        env_file = ".env"

settings = Settings()
```

**backend/app/services/tracing.py:**
```python
from langfuse import Langfuse
from app.config import settings

class TracingService:
    def __init__(self):
        self.langfuse = Langfuse(
            public_key=settings.langfuse_public_key,
            secret_key=settings.langfuse_secret_key,
            host=settings.langfuse_host
        )
        self.project_id = settings.langfuse_project_id

    def trace_operation(self, name: str, **kwargs):
        """Create trace in MediaVault project"""
        return self.langfuse.trace(
            name=name,
            project_id=self.project_id,
            **kwargs
        )
```

### Option 2: Shared Project with Tags

**Use existing project but tag all MediaVault traces:**

```python
class TracingService:
    def trace_operation(self, name: str, **kwargs):
        return self.langfuse.trace(
            name=name,
            tags=["mediavault", "nas-scanner"],  # Tag all traces
            metadata={
                "app": "mediavault",
                "version": "0.1.0",
                **kwargs.get("metadata", {})
            },
            **kwargs
        )
```

**Then filter in Langfuse UI:**
- Go to Traces
- Filter by tag: `mediavault`
- Or search: `metadata.app:"mediavault"`

---

## Tagging Strategy (Recommended)

Even with dedicated project, use tags for organization:

```python
# NAS Scan
trace = tracing.trace_operation(
    name="nas_scan",
    tags=["scanner", "nas", "full-scan"],
    metadata={"paths": ["/volume1/docker", "/volume1/videos"]}
)

# Duplicate Detection
trace = tracing.trace_operation(
    name="duplicate_detection",
    tags=["deduplication", "fuzzy-match"],
    metadata={"threshold": 85, "files_scanned": 1247}
)

# Chat Query
trace = tracing.trace_operation(
    name="chat_query",
    tags=["chat", "azure-openai", "gpt-4o"],
    metadata={"model": "gpt-4o", "user_question": "How many 4K movies?"}
)

# Archive Operation
trace = tracing.trace_operation(
    name="archive_file",
    tags=["archive", "file-operation"],
    metadata={"file_id": 123, "reason": "duplicate"}
)
```

---

## Langfuse UI Navigation

### Once Project is Created

**Project URL Format:**
```
https://langfuse.orourkes.me/project/{project_id}/traces
```

**Example (once you get new project ID):**
```
https://langfuse.orourkes.me/project/cmXXXXXXXXXX/traces
```

**Sections Available:**
- **Traces:** All operations tracked
- **Sessions:** Group related traces (e.g., single NAS scan)
- **Generations:** LLM API calls (Azure OpenAI)
- **Datasets:** Test data (optional)
- **Prompts:** Prompt templates (for chat feature)
- **Settings:** API keys, project config

---

## Migration: Move Current Session to MediaVault Project

**Unfortunately:** Cannot move traces between projects retroactively

**Current session** (`60744d29-5fcc-4dae-b401-e75246b4cdfc`) will stay in "Bimodal Agent" project.

**Solution:**
- Future MediaVault backend traces → New "mediavault" project
- Planning sessions (like this one) → Stay in current project
- Document which traces are where

---

## Quick Start Guide (After Creating Project)

### 1. Create Project in Langfuse Web UI
```
Name: mediavault
Description: Media organization and deduplication system
```

### 2. Copy API Keys to .env
```bash
cd /home/mercury/projects/mediavault
nano .env

# Add these lines:
LANGFUSE_PUBLIC_KEY=pk-lf-XXXXXXXXX
LANGFUSE_SECRET_KEY=sk-lf-XXXXXXXXX
LANGFUSE_HOST=http://10.27.10.104:3010
LANGFUSE_PROJECT_ID=cmXXXXXXXXXXXX
```

### 3. Update Documentation
```bash
# Update TRACEFORGE_INTEGRATION.md with new project ID
nano TRACEFORGE_INTEGRATION.md
```

### 4. Test Connection (When Backend Built)
```python
from langfuse import Langfuse

langfuse = Langfuse(
    public_key="pk-lf-...",
    secret_key="sk-lf-...",
    host="http://10.27.10.104:3010"
)

# Test trace
trace = langfuse.trace(
    name="test_connection",
    metadata={"test": "Hello from MediaVault"}
)
langfuse.flush()

print(f"Trace created: {trace.id}")
```

---

## Project Comparison (Both Under "Minerva" Organization)

### Current: "Bimodal Agent" Project
**Organization:** Minerva
**Project ID:** `cmhapoi2p00067fp318zwhsl4`
**Contains:**
- Bimodal agent traces
- Claude Code planning sessions (like this one)
- Mixed application traces

**URL:**
https://langfuse.orourkes.me/project/cmhapoi2p00067fp318zwhsl4/traces

### Future: "MediaVault" Project
**Organization:** Minerva (same organization)
**Project ID:** `cmXXXXXXXXXXXX` (get after creation)
**Will Contain:**
- NAS scan operations
- Duplicate detection runs
- Azure OpenAI chat queries
- Archive operations
- MediaVault-specific traces only

**URL:**
https://langfuse.orourkes.me/project/cmXXXXXXXXXXXX/traces

**Benefits of Same Organization:**
- Shared billing/usage across projects
- Unified user management
- Organization-wide analytics (if needed)
- Easy switching between projects in UI

---

## Recommended Approach

### For Now (Planning Phase)
✅ Keep current session in "Bimodal Agent" project
- Planning is related to development work
- Not production MediaVault operations

### When Backend is Built
✅ Create dedicated "mediavault" project
- Cleaner separation
- Easier analytics
- Independent cost tracking

### Tagging for Both
✅ Always tag traces with:
- Application: `mediavault`
- Operation type: `scanner`, `deduplication`, `chat`, `archive`
- Environment: `development`, `production`

---

## Next Steps

### Immediate (Before Building Backend)
1. **Manually create "mediavault" project in Langfuse UI:**
   - Go to https://langfuse.orourkes.me
   - Settings → New Project
   - Name: `mediavault`

2. **Copy API keys and project ID**

3. **Update `.env.example` with placeholders:**
   ```bash
   # Langfuse MediaVault Project
   LANGFUSE_PUBLIC_KEY=pk-lf-YOUR_KEY_HERE
   LANGFUSE_SECRET_KEY=sk-lf-YOUR_SECRET_HERE
   LANGFUSE_HOST=http://10.27.10.104:3010
   LANGFUSE_PROJECT_ID=cm_YOUR_PROJECT_ID
   ```

4. **Create actual `.env` file with real keys**

### When Building Backend (Next Session)
1. Integrate Langfuse SDK
2. Create TracingService class
3. Instrument scanner, chat, archive services
4. Test with first NAS scan
5. Verify traces appear in new "mediavault" project

---

## Verification Commands

### After Creating Project

**Check project exists (via UI):**
```
https://langfuse.orourkes.me/settings/projects
```

**Test API connection (when backend built):**
```bash
# From backend container
python -c "
from langfuse import Langfuse
l = Langfuse(
    public_key='pk-lf-...',
    secret_key='sk-lf-...',
    host='http://10.27.10.104:3010'
)
trace = l.trace(name='test')
l.flush()
print(f'Success! Trace ID: {trace.id}')
"
```

**View traces:**
```
https://langfuse.orourkes.me/project/{new_project_id}/traces
```

---

## Summary

**Current State:**
- This planning session: In "Bimodal Agent" project ✅
- No MediaVault backend traces yet (not built)

**Action Required:**
1. Create "mediavault" project in Langfuse UI (manual)
2. Get API keys and project ID
3. Add to `.env` file

**Future State:**
- Planning sessions: Stay in "Bimodal Agent" project
- MediaVault operations: New "mediavault" project
- Clear separation, easy analytics

**I cannot create the project via API** (requires auth), but I've provided complete instructions for manual creation!

Would you like me to:
1. Wait for you to create the project and provide the keys?
2. Proceed with using the existing "Bimodal Agent" project for now?
3. Set up configuration assuming a new project will be created?
