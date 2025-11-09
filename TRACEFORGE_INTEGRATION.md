# MediaVault - TraceForge/Langfuse Integration

**Created:** 2025-11-08
**Purpose:** Document observability integration for MediaVault project

---

## Current Session Tracking

### This Planning Session
**Session ID:** `60744d29-5fcc-4dae-b401-e75246b4cdfc`
**Project:** `projects` (Langfuse project ID: `cmhapoi2p00067fp318zwhsl4`)
**Status:** ✅ Being tracked by TraceForge

**View in Langfuse:**
https://langfuse.orourkes.me/project/cmhapoi2p00067fp318zwhsl4/traces?peek=60744d29-5fcc-4dae-b401-e75246b4cdfc&timestamp=2025-11-08T13:18:17.297Z

**What's Being Tracked:**
- All tool calls (Bash, Read, Write, Edit)
- User messages and prompts
- Claude responses
- Tool execution times
- Database operations (create database, migrations)
- File creations (documentation, schemas)

**Local Session Data:**
- File: `/tmp/traceforge-session-60744d29-5fcc-4dae-b401-e75246b4cdfc.json`
- Hooks log: `/tmp/traceforge-hooks.log`

---

## Langfuse URL Structure

### ❌ Incorrect Format (404 Error)
```
https://langfuse.orourkes.me/traces/{trace_id}
```
**Problem:** Missing project context - Langfuse is project-scoped

### ✅ Correct Format
```
https://langfuse.orourkes.me/project/{project_id}/traces?peek={trace_id}&timestamp={iso_timestamp}
```

**Components:**
- **Base URL:** `https://langfuse.orourkes.me`
- **Project ID:** `cmhapoi2p00067fp318zwhsl4` (your main "projects" workspace)
- **Trace ID:** Session ID or trace ID
- **Timestamp:** ISO 8601 format (optional, helps with navigation)

### Example URLs

**View all traces in project:**
```
https://langfuse.orourkes.me/project/cmhapoi2p00067fp318zwhsl4/traces
```

**Peek at specific trace:**
```
https://langfuse.orourkes.me/project/cmhapoi2p00067fp318zwhsl4/traces?peek={session_id}
```

**Filter by date:**
```
https://langfuse.orourkes.me/project/cmhapoi2p00067fp318zwhsl4/traces?timestamp=2025-11-08T13:18:17.297Z
```

---

## TraceForge Architecture

### How It Works

```
┌─────────────────────────────────────────────────────────────┐
│  Claude Code Session                                        │
│  - User prompts                                             │
│  - Tool calls (Bash, Read, Write, etc.)                     │
│  - Claude responses                                         │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│  TraceForge Hooks (.claude/settings.local.json)             │
│  - SessionStart hook                                        │
│  - UserPromptSubmit hook                                    │
│  - ToolUse hook                                             │
│  - Response hook                                            │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│  Local Logging                                              │
│  - /tmp/traceforge-session-{id}.json                        │
│  - /tmp/traceforge-hooks.log                                │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│  TraceForge API (Optional)                                  │
│  - http://10.27.10.104:3011                                 │
│  - Centralizes traces from multiple sources                 │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│  Langfuse Server                                            │
│  - http://10.27.10.104:3010 (internal)                      │
│  - https://langfuse.orourkes.me (external)                  │
│  - PostgreSQL storage                                       │
│  - Web UI for viewing traces                                │
└─────────────────────────────────────────────────────────────┘
```

### Components

1. **Hooks** - Capture events from Claude Code
2. **Local Files** - Session metadata and logs
3. **TraceForge API** - Centralized collection (optional)
4. **Langfuse Server** - Storage and visualization

---

## Logged Events (This Session)

**From `/tmp/traceforge-hooks.log`:**

```
2025-11-08 10:49:24 - Logging user message for session 60744d29...
2025-11-08 10:49:33 - Logging tool use: Bash for session 60744d29...
2025-11-08 10:49:34 - Logging tool use: Bash for session 60744d29...
2025-11-08 10:49:40 - Logging tool use: Bash for session 60744d29...
2025-11-08 10:49:41 - Logging tool use: Read for session 60744d29...
2025-11-08 10:51:33 - Logging tool use: Write for session 60744d29...
2025-11-08 10:51:34 - Logging tool use: Write for session 60744d29...
2025-11-08 10:51:48 - Logging tool use: Bash for session 60744d29...
2025-11-08 10:52:08 - Logging Claude response for session 60744d29...
... (18+ events logged)
```

**Events Captured:**
- User messages (your prompts)
- Tool uses (Bash, Read, Write, Edit)
- Claude responses
- Timestamps for performance analysis

---

## Future: MediaVault Backend Observability

### When MediaVault Will Generate Traces

Once we build the MediaVault backend, it will generate traces for:

1. **NAS Scanning Operations**
   - File discovery (recursive walk)
   - FFprobe metadata extraction
   - MD5 hash calculation
   - TMDb API lookups
   - Database insertions

2. **Duplicate Detection**
   - Fuzzy matching algorithm runs
   - Quality score calculations
   - Language detection
   - Grouping operations

3. **Azure OpenAI Chat**
   - User questions
   - Context injection (database queries)
   - GPT-4o API calls
   - Token usage tracking
   - Cost tracking

4. **Archive Operations**
   - File moves to temp staging
   - Deletion decisions
   - Restore operations

### Implementation Plan

**Add to backend dependencies:**
```python
# requirements.txt
langfuse>=2.0.0
opentelemetry-api>=1.20.0
opentelemetry-sdk>=1.20.0
```

**Backend configuration (.env):**
```bash
# Langfuse
LANGFUSE_PUBLIC_KEY=pk-lf-... (from bimodal_agent)
LANGFUSE_SECRET_KEY=sk-lf-... (from bimodal_agent)
LANGFUSE_HOST=http://10.27.10.104:3010

# TraceForge API (optional)
TRACEFORGE_API_URL=http://10.27.10.104:3011
TRACEFORGE_ENABLED=true
```

**Backend integration:**
```python
# backend/app/services/tracing.py

from langfuse import Langfuse
from contextlib import contextmanager

class TracingService:
    def __init__(self):
        self.langfuse = Langfuse(
            public_key=settings.LANGFUSE_PUBLIC_KEY,
            secret_key=settings.LANGFUSE_SECRET_KEY,
            host=settings.LANGFUSE_HOST
        )

    @contextmanager
    def trace_operation(self, name: str, metadata: dict = None):
        """
        Context manager for tracing long-running operations

        Usage:
            with tracing.trace_operation("nas_scan", {"path": "/volume1/videos"}):
                # do work
                pass
        """
        trace = self.langfuse.trace(
            name=name,
            metadata=metadata or {},
            project_id="cmhapoi2p00067fp318zwhsl4"  # MediaVault project
        )

        try:
            yield trace
            trace.update(status="success")
        except Exception as e:
            trace.update(status="error", metadata={"error": str(e)})
            raise
        finally:
            self.langfuse.flush()

    def trace_llm_call(self, model: str, messages: list, response: dict):
        """
        Trace Azure OpenAI chat calls

        Usage:
            tracing.trace_llm_call(
                model="gpt-4o",
                messages=[{"role": "user", "content": "How many 4K movies?"}],
                response={"content": "You have 127...", "tokens": 50}
            )
        """
        self.langfuse.generation(
            name="chat_completion",
            model=model,
            input=messages,
            output=response.get("content"),
            usage={
                "prompt_tokens": response.get("prompt_tokens", 0),
                "completion_tokens": response.get("completion_tokens", 0),
                "total_tokens": response.get("total_tokens", 0)
            },
            metadata={
                "finish_reason": response.get("finish_reason"),
                "model_version": model
            }
        )
        self.langfuse.flush()

# backend/app/services/scanner_service.py

class ScannerService:
    def __init__(self, tracing: TracingService):
        self.tracing = tracing

    async def scan_nas(self, paths: list):
        """Scan NAS with tracing"""
        with self.tracing.trace_operation("nas_scan", {"paths": paths}):
            # Scanning logic
            files_found = await self._scan_recursive(paths)

            # Update trace with results
            trace.update(metadata={
                "files_found": len(files_found),
                "scan_duration_seconds": duration
            })

            return files_found
```

### Example Traces (Future)

**NAS Scan Trace:**
```
Operation: nas_scan
Duration: 3m 45s
Input: {paths: ["/volume1/docker", "/volume1/videos"]}
Output: {files_found: 1247, new_files: 23, updated_files: 5}
Status: success
```

**Chat Query Trace:**
```
Operation: chat_completion
Model: gpt-4o
Input: "How many 4K movies do I have?"
Output: "You have 127 4K movies in your library..."
Tokens: {prompt: 245, completion: 42, total: 287}
Cost: $0.0042
Status: success
```

**Duplicate Detection Trace:**
```
Operation: duplicate_detection
Duration: 1m 12s
Input: {fuzzy_threshold: 85, files_scanned: 1247}
Output: {duplicate_groups: 34, files_duplicated: 89}
Metadata: {
  exact_matches: 12,
  fuzzy_matches: 22,
  requires_review: 7
}
Status: success
```

---

## Benefits of Tracing MediaVault

1. **Performance Monitoring**
   - Track scan duration over time
   - Identify slow operations (FFprobe, hash calculation)
   - Optimize bottlenecks

2. **Cost Tracking**
   - Monitor Azure OpenAI token usage
   - Track TMDb API call counts
   - Budget management

3. **Debugging**
   - Trace failed scans
   - Understand duplicate detection logic
   - Replay operations

4. **User Insights**
   - Most common chat queries
   - Feature usage patterns
   - Error frequency

5. **Audit Trail**
   - Who deleted what files
   - When scans were run
   - Archive operation history

---

## Langfuse Projects

### Current Project Structure
**Project ID:** `cmhapoi2p00067fp318zwhsl4`
**Name:** "projects" (or similar)

**Contains Traces From:**
- Claude Code sessions (like this one)
- Potentially bimodal_agent runs
- Future: MediaVault backend operations

### Option: Separate MediaVault Project

**Should we create a dedicated Langfuse project for MediaVault?**

**Pros:**
- Cleaner separation of concerns
- Easier filtering (all MediaVault traces in one place)
- Independent analytics

**Cons:**
- More projects to manage
- May want unified view of all "projects" activity

**Recommendation:** Start with existing project, create separate later if needed.

---

## Commands Reference

### View This Session
```bash
# Langfuse Web UI
open https://langfuse.orourkes.me/project/cmhapoi2p00067fp318zwhsl4/traces?peek=60744d29-5fcc-4dae-b401-e75246b4cdfc

# Local session file
cat /tmp/traceforge-session-60744d29-5fcc-4dae-b401-e75246b4cdfc.json

# Hook logs (filtered)
grep "60744d29-5fcc-4dae-b401-e75246b4cdfc" /tmp/traceforge-hooks.log
```

### View All Recent Traces
```bash
# All sessions today
ls -lt /tmp/traceforge-session-*.json | head -10

# All recent hook events
tail -100 /tmp/traceforge-hooks.log
```

### Search Traces in Langfuse
1. Go to: https://langfuse.orourkes.me/project/cmhapoi2p00067fp318zwhsl4/traces
2. Filter by:
   - Date range
   - Session ID
   - User
   - Status (success/error)
   - Tags

---

## Next Steps

### For MediaVault Backend (Next Session)
1. Add Langfuse SDK to requirements.txt
2. Create TracingService class
3. Instrument scanner service
4. Instrument chat service
5. Add trace metadata (file counts, durations, costs)
6. Test with initial NAS scan

### Configuration
```bash
# Add to .env
LANGFUSE_PUBLIC_KEY=pk-lf-ab2d7168-4003-498b-874a-43ee4fc6207e
LANGFUSE_SECRET_KEY=sk-lf-dc1e9589-687f-43ed-945e-af9df0908a90
LANGFUSE_HOST=http://10.27.10.104:3010
LANGFUSE_PROJECT_ID=cmhapoi2p00067fp318zwhsl4
```

---

## Conclusion

**This planning session IS being tracked:**
- ✅ 18+ events logged to TraceForge
- ✅ Viewable in Langfuse at correct URL (project-scoped)
- ✅ Local session data preserved

**Future MediaVault backend WILL be instrumented:**
- NAS scans
- Duplicate detection
- Azure OpenAI chat
- Archive operations
- Full observability with cost tracking

**Trace URL Format:**
```
https://langfuse.orourkes.me/project/{project_id}/traces?peek={trace_id}
```

**This Session:**
https://langfuse.orourkes.me/project/cmhapoi2p00067fp318zwhsl4/traces?peek=60744d29-5fcc-4dae-b401-e75246b4cdfc&timestamp=2025-11-08T13:18:17.297Z
