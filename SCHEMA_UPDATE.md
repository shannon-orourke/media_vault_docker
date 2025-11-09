# MediaVault - Database Schema Update

## Additional Core Table: `pending_deletions`

**Purpose:** Staging area for files marked for deletion before permanent purge

```sql
CREATE TABLE pending_deletions (
    id SERIAL PRIMARY KEY,

    -- File reference
    file_id INTEGER NOT NULL,
    duplicate_group_id INTEGER,

    -- Deletion metadata
    original_filepath TEXT NOT NULL,
    temp_filepath TEXT NOT NULL,          -- /volume1/video/duplicates_before_purge/{media_type}/{date}/...

    -- Deletion reasoning (critical for review)
    deletion_reason TEXT NOT NULL,        -- Human-readable explanation
    deletion_category VARCHAR(50),        -- 'lower_quality', 'duplicate_exact', 'duplicate_fuzzy', 'wrong_language', 'corrupted'

    -- Quality comparison (if duplicate)
    kept_file_id INTEGER,                 -- FK to media_files.id (the file we're keeping)
    kept_file_quality_score DECIMAL(6,2),
    deleted_file_quality_score DECIMAL(6,2),
    quality_difference DECIMAL(6,2),      -- Positive = kept file is better

    -- Language tracking (CRITICAL)
    audio_languages TEXT[],               -- ['en', 'es', 'fr'] from mediainfo
    subtitle_languages TEXT[],            -- ['en', 'en-sdh', 'es']
    has_english_audio BOOLEAN,
    has_english_subtitles BOOLEAN,
    is_foreign_film BOOLEAN DEFAULT false, -- Non-English movie with subtitles (keep regardless)

    -- Decision context
    decision_confidence VARCHAR(20),      -- 'certain', 'review_recommended', 'uncertain'
    requires_manual_review BOOLEAN DEFAULT false,

    -- User decision tracking
    reviewed BOOLEAN DEFAULT false,
    reviewed_by INTEGER,                  -- FK to users.id
    reviewed_at TIMESTAMP,
    review_notes TEXT,

    -- Final action
    final_action VARCHAR(20),             -- 'deleted', 'restored', 'kept_both', 'pending'
    deleted_permanently_at TIMESTAMP,

    -- Timestamps
    moved_to_temp_at TIMESTAMP DEFAULT NOW(),
    scheduled_deletion_at TIMESTAMP,      -- Auto-delete after X days if not reviewed

    -- Constraints
    CONSTRAINT fk_file_pending FOREIGN KEY (file_id)
        REFERENCES media_files(id) ON DELETE CASCADE,
    CONSTRAINT fk_kept_file FOREIGN KEY (kept_file_id)
        REFERENCES media_files(id) ON DELETE SET NULL,
    CONSTRAINT fk_duplicate_group_pending FOREIGN KEY (duplicate_group_id)
        REFERENCES duplicate_groups(id) ON DELETE SET NULL,
    CONSTRAINT fk_reviewed_by FOREIGN KEY (reviewed_by)
        REFERENCES users(id) ON DELETE SET NULL
);

CREATE INDEX idx_pending_deletions_file ON pending_deletions(file_id);
CREATE INDEX idx_pending_deletions_reviewed ON pending_deletions(reviewed);
CREATE INDEX idx_pending_deletions_action ON pending_deletions(final_action);
CREATE INDEX idx_pending_deletions_scheduled ON pending_deletions(scheduled_deletion_at);
CREATE INDEX idx_pending_deletions_requires_review ON pending_deletions(requires_manual_review);
```

---

## Updated `media_files` Table - Add Language Tracking

```sql
ALTER TABLE media_files ADD COLUMN audio_languages TEXT[];
ALTER TABLE media_files ADD COLUMN subtitle_languages TEXT[];
ALTER TABLE media_files ADD COLUMN has_english_audio BOOLEAN DEFAULT false;
ALTER TABLE media_files ADD COLUMN has_english_subtitles BOOLEAN DEFAULT false;
ALTER TABLE media_files ADD COLUMN is_foreign_film BOOLEAN DEFAULT false;
ALTER TABLE media_files ADD COLUMN language_detected_at TIMESTAMP;

-- Index for language filtering
CREATE INDEX idx_media_files_english_audio ON media_files(has_english_audio);
CREATE INDEX idx_media_files_foreign_film ON media_files(is_foreign_film);
```

---

## Deletion Reasoning Examples

### Category: `lower_quality`
**Deletion Reason Examples:**
- "Kept 4K version (3840x2160, H.265, 25 Mbps). Deleted 1080p version (1920x1080, H.264, 8 Mbps). Quality difference: +75.2 points."
- "Kept file with 5.1 audio (AAC, 640 kbps). Deleted file with stereo audio (MP3, 128 kbps)."
- "Kept HDR10 version. Deleted SDR version of same film."

### Category: `duplicate_exact`
**Deletion Reason Examples:**
- "Exact MD5 match (abc123def456). Files are byte-for-byte identical. Keeping /volume1/videos/Movies/Inception.mkv, deleting duplicate at /volume1/docker/media/Inception.mkv."

### Category: `duplicate_fuzzy`
**Deletion Reason Examples:**
- "Same show S01E01 detected (fuzzy match 95% confidence). Kept higher quality version."
- "Red Dwarf S01E01: Kept 'RedDwarf_s01e01_Wondercrew.mkv' (720p, H.264), deleted 'RedDwwarf_TVLab_s01e01.avi' (480p, MPEG4)."

### Category: `wrong_language`
**Deletion Reason Examples:**
- "Deleted Spanish audio version (no English audio, no English subtitles). Not a foreign film. Kept English version."
- "Deleted French dub (audio: ['fr']). English version available with better quality."
- "**REQUIRES REVIEW**: Deleting higher quality file (1080p) because it lacks English audio. Lower quality (720p) has English. Confidence: uncertain."

### Category: `foreign_film` (KEEP, not delete)
**Reasoning for NOT deleting:**
- "Foreign film detected: Parasite (Korean, 2019). Has English subtitles. Keeping despite non-English audio."
- "Original language version of French film. Marked is_foreign_film=true. Will not auto-delete."

---

## Language Detection Logic

### From MediaInfo (Python `pymediainfo`)
```python
from pymediainfo import MediaInfo

def extract_languages(filepath: str) -> dict:
    """
    Extract audio and subtitle languages from video file
    """
    media_info = MediaInfo.parse(filepath)

    audio_languages = []
    subtitle_languages = []

    for track in media_info.tracks:
        if track.track_type == "Audio":
            if track.language:
                audio_languages.append(track.language)  # ISO 639-2 codes

        elif track.track_type == "Text":  # Subtitles
            if track.language:
                subtitle_languages.append(track.language)

    # Normalize to ISO 639-1 (en, es, fr)
    audio_languages = [normalize_language(lang) for lang in audio_languages]
    subtitle_languages = [normalize_language(lang) for lang in subtitle_languages]

    has_english_audio = 'en' in audio_languages
    has_english_subtitles = 'en' in subtitle_languages or 'en-sdh' in subtitle_languages

    # Heuristic: if only non-English audio but has English subs, likely foreign film
    is_foreign_film = (
        not has_english_audio and
        has_english_subtitles and
        len(audio_languages) == 1
    )

    return {
        'audio_languages': audio_languages,
        'subtitle_languages': subtitle_languages,
        'has_english_audio': has_english_audio,
        'has_english_subtitles': has_english_subtitles,
        'is_foreign_film': is_foreign_film
    }
```

---

## Deletion Decision Rules (Automated)

### Rule 1: Exact Duplicates (MD5 match)
```
IF md5_hash matches AND both files have English audio:
  → Keep file with higher quality_score
  → Deletion confidence: CERTAIN
  → Category: duplicate_exact
```

### Rule 2: Quality-based (Same show/episode)
```
IF same show+season+episode AND both have English audio:
  → Keep file with higher quality_score
  → Deletion confidence: CERTAIN
  → Category: lower_quality

IF quality difference > 50 points:
  → Auto-approve deletion
ELSE IF quality difference < 20 points:
  → requires_manual_review = true
  → Deletion confidence: UNCERTAIN
```

### Rule 3: Language-based (CRITICAL)
```
IF file has NO English audio AND NO English subtitles AND is_foreign_film = false:
  → Check if English version exists
  → IF English version exists:
      → Delete non-English version
      → Category: wrong_language
      → Deletion confidence: CERTAIN
  → ELSE:
      → requires_manual_review = true
      → Reason: "Only available version is non-English"

IF file has NO English audio BUT has English subtitles:
  → is_foreign_film = true (heuristic)
  → DO NOT auto-delete
  → Keep higher quality version

IF comparing two files of same show:
  → IF one has English audio, other doesn't:
      → Keep English version EVEN IF lower quality
      → UNLESS quality difference > 100 points (4K vs 480p)
          → Then requires_manual_review = true
```

### Rule 4: Three+ Duplicates (Same quality tier)
```
IF 3 files with same show+season+episode:
  → Rank by quality_score
  → Keep highest
  → Delete 2nd and 3rd
  → Deletion reason: "Kept highest quality (#1 of 3). Files #2 and #3 are redundant."
  → Deletion confidence: CERTAIN (if quality difference > 10 points)
  → Deletion confidence: REVIEW_RECOMMENDED (if quality scores within 5 points)
```

---

## Chat with Your Data - Azure OpenAI Integration

### New Table: `chat_sessions`

```sql
CREATE TABLE chat_sessions (
    id SERIAL PRIMARY KEY,

    user_id INTEGER NOT NULL,
    session_id UUID UNIQUE NOT NULL DEFAULT gen_random_uuid(),

    -- Chat metadata
    title VARCHAR(255),                   -- Auto-generated from first message
    context_type VARCHAR(50),             -- 'library', 'duplicates', 'general'

    -- Azure OpenAI tracking
    model VARCHAR(50) DEFAULT 'gpt-4o',   -- gpt-4o, gpt-4o-mini
    total_tokens_used INTEGER DEFAULT 0,
    total_cost DECIMAL(10,4) DEFAULT 0.0, -- USD

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    last_message_at TIMESTAMP DEFAULT NOW(),

    CONSTRAINT fk_chat_user FOREIGN KEY (user_id)
        REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX idx_chat_sessions_user ON chat_sessions(user_id);
CREATE INDEX idx_chat_sessions_last_message ON chat_sessions(last_message_at DESC);
```

### New Table: `chat_messages`

```sql
CREATE TABLE chat_messages (
    id SERIAL PRIMARY KEY,

    session_id INTEGER NOT NULL,

    -- Message content
    role VARCHAR(20) NOT NULL,            -- 'user', 'assistant', 'system'
    content TEXT NOT NULL,

    -- Context injection (for RAG)
    context_data JSONB,                   -- Relevant files, duplicates, stats injected as context
    context_query TEXT,                   -- SQL query used to fetch context

    -- Azure OpenAI metadata
    model VARCHAR(50),
    prompt_tokens INTEGER,
    completion_tokens INTEGER,
    total_tokens INTEGER,
    finish_reason VARCHAR(50),            -- 'stop', 'length', 'content_filter'

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),

    CONSTRAINT fk_chat_session FOREIGN KEY (session_id)
        REFERENCES chat_sessions(id) ON DELETE CASCADE
);

CREATE INDEX idx_chat_messages_session ON chat_messages(session_id);
CREATE INDEX idx_chat_messages_created ON chat_messages(created_at);
```

---

## Chat Features

### 1. Natural Language Queries
**User asks:** "How many 4K movies do I have?"

**Backend:**
1. Parse intent → "count media files where resolution is 4K"
2. Generate SQL:
   ```sql
   SELECT COUNT(*) FROM media_files
   WHERE media_type = 'movie' AND quality_tier = '4K' AND status = 'active';
   ```
3. Execute query → `127 movies`
4. Inject result as context to GPT-4o
5. GPT-4o response: "You have 127 4K movies in your library."

### 2. Duplicate Investigation
**User asks:** "Why did you suggest deleting Inception (2010)?"

**Backend:**
1. Search pending_deletions for "Inception"
2. Fetch deletion_reason, kept_file_id, quality scores
3. Inject as context:
   ```json
   {
     "deleted_file": {
       "filepath": "/volume1/docker/Inception.2010.1080p.mkv",
       "quality_score": 95.5,
       "resolution": "1080p",
       "codec": "H.264"
     },
     "kept_file": {
       "filepath": "/volume1/videos/Movies/Inception.2010.2160p.mkv",
       "quality_score": 170.3,
       "resolution": "4K",
       "codec": "H.265"
     },
     "reason": "Kept 4K version with higher quality score (+74.8 points)"
   }
   ```
4. GPT-4o explains the decision with full context

### 3. Intelligent Recommendations
**User asks:** "What duplicates should I review manually?"

**Backend:**
1. Query:
   ```sql
   SELECT * FROM pending_deletions
   WHERE requires_manual_review = true
   ORDER BY quality_difference ASC
   LIMIT 10;
   ```
2. Inject results as context
3. GPT-4o summarizes with reasoning

### 4. Library Insights
**User asks:** "What's taking up the most space?"

**Backend:**
1. Query:
   ```sql
   SELECT show_name, SUM(file_size) as total_size, COUNT(*) as file_count
   FROM media_files
   WHERE media_type = 'tv' AND status = 'active'
   GROUP BY show_name
   ORDER BY total_size DESC
   LIMIT 10;
   ```
2. GPT-4o formats as human-readable response with GB conversions

---

## Azure OpenAI Configuration for Chat

### `.env` Update
```bash
# From bimodal_agent project (reuse)
AZURE_OPENAI_KEY=9abCh0KH4swF6vplFQ5GYIOQ6XqYTht6PZQ7xCVK4KtKG0m31UyxJQQJ99BJACYeBjFXJ3w3AAABACOGmjSQ
AZURE_OPENAI_ENDPOINT=https://eastus.api.cognitive.microsoft.com/
AZURE_OPENAI_API_VERSION=2024-08-01-preview

# Chat model deployment
AZURE_DEPLOYMENT_NAME_CHAT=gpt-4o
AZURE_DEPLOYMENT_NAME_CHAT_MINI=gpt-4o-mini  # For cheaper queries
```

### Chat Service Implementation

```python
from openai import AzureOpenAI
import json

class ChatService:
    def __init__(self):
        self.client = AzureOpenAI(
            api_key=os.getenv("AZURE_OPENAI_KEY"),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
        )
        self.model = os.getenv("AZURE_DEPLOYMENT_NAME_CHAT", "gpt-4o")

    async def chat(self, user_message: str, session_id: int) -> str:
        """
        Process user message with database context
        """
        # 1. Load chat history
        history = await self.load_history(session_id)

        # 2. Detect intent and fetch relevant data
        context = await self.fetch_context(user_message)

        # 3. Build messages with system prompt
        messages = [
            {
                "role": "system",
                "content": self.get_system_prompt(context)
            },
            *history,
            {
                "role": "user",
                "content": user_message
            }
        ]

        # 4. Call Azure OpenAI
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.7,
            max_tokens=1000
        )

        # 5. Save to database
        await self.save_message(session_id, "user", user_message, context)
        await self.save_message(
            session_id,
            "assistant",
            response.choices[0].message.content,
            response.usage
        )

        return response.choices[0].message.content

    def get_system_prompt(self, context: dict) -> str:
        return f"""You are MediaVault Assistant, an AI helper for managing a media library.

You have access to the user's media database. Here's the current context:

**Library Statistics:**
- Total files: {context.get('total_files', 'N/A')}
- Total size: {context.get('total_size_gb', 'N/A')} GB
- Movies: {context.get('movie_count', 'N/A')}
- TV Shows: {context.get('tv_show_count', 'N/A')}
- Pending deletions: {context.get('pending_deletions', 'N/A')}

**Relevant Data for this Query:**
{json.dumps(context.get('query_results', {}), indent=2)}

Your role:
- Answer questions about the media library
- Explain duplicate detection decisions
- Provide insights on storage usage
- Recommend actions for manual review
- Be concise and helpful

Always cite specific data from the context when answering."""

    async def fetch_context(self, user_message: str) -> dict:
        """
        Determine what data to fetch based on user question
        """
        # Intent detection (simple keyword-based, can be enhanced with embeddings)
        message_lower = user_message.lower()

        context = {}

        # General stats (always include)
        context.update(await self.get_library_stats())

        # Specific queries based on keywords
        if "4k" in message_lower or "resolution" in message_lower:
            context['query_results'] = await self.get_resolution_breakdown()

        elif "duplicate" in message_lower:
            context['query_results'] = await self.get_duplicate_summary()

        elif "space" in message_lower or "storage" in message_lower:
            context['query_results'] = await self.get_storage_hogs()

        elif "delete" in message_lower or "review" in message_lower:
            context['query_results'] = await self.get_pending_deletions()

        # Check for specific show/movie names (fuzzy search)
        elif any(word in message_lower for word in ["show", "movie", "film"]):
            # Extract potential title from message
            potential_title = self.extract_title(user_message)
            if potential_title:
                context['query_results'] = await self.search_media(potential_title)

        return context
```

---

## API Endpoints for Chat

```python
# backend/app/routes/chat.py

@router.post("/chat/sessions")
async def create_chat_session(
    user_id: int,
    db: Session = Depends(get_db)
) -> ChatSessionResponse:
    """Create new chat session"""
    ...

@router.post("/chat/sessions/{session_id}/messages")
async def send_message(
    session_id: int,
    message: ChatMessageRequest,
    db: Session = Depends(get_db)
) -> ChatMessageResponse:
    """Send message and get AI response"""
    chat_service = ChatService()
    response = await chat_service.chat(message.content, session_id)
    return {"role": "assistant", "content": response}

@router.get("/chat/sessions/{session_id}/messages")
async def get_chat_history(
    session_id: int,
    db: Session = Depends(get_db)
) -> List[ChatMessageResponse]:
    """Retrieve chat history"""
    ...
```

---

## Frontend Chat Component (React)

```tsx
// components/ChatInterface.tsx

import { useState } from 'react';
import { Textarea, Button, Stack, Paper, Text } from '@mantine/core';
import { IconSend } from '@tabler/icons-react';

export function ChatInterface({ sessionId }: { sessionId: number }) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);

  const sendMessage = async () => {
    if (!input.trim()) return;

    const userMessage = { role: 'user', content: input };
    setMessages([...messages, userMessage]);
    setInput('');
    setLoading(true);

    try {
      const response = await fetch(`/api/chat/sessions/${sessionId}/messages`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content: input })
      });

      const assistantMessage = await response.json();
      setMessages([...messages, userMessage, assistantMessage]);
    } catch (error) {
      console.error('Chat error:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Stack>
      <Paper p="md" style={{ height: '500px', overflowY: 'auto' }}>
        {messages.map((msg, idx) => (
          <Text key={idx} color={msg.role === 'user' ? 'blue' : 'gray'}>
            <strong>{msg.role}:</strong> {msg.content}
          </Text>
        ))}
      </Paper>

      <Textarea
        value={input}
        onChange={(e) => setInput(e.target.value)}
        placeholder="Ask about your media library..."
        onKeyPress={(e) => e.key === 'Enter' && !e.shiftKey && sendMessage()}
      />

      <Button onClick={sendMessage} loading={loading} leftIcon={<IconSend />}>
        Send
      </Button>
    </Stack>
  );
}
```

---

## Summary of Changes

### New Tables Added:
1. **pending_deletions** - Staging area before permanent deletion
2. **chat_sessions** - Track AI chat sessions
3. **chat_messages** - Store conversation history

### Updated Tables:
1. **media_files** - Added language columns (audio_languages, subtitle_languages, has_english_audio, has_english_subtitles, is_foreign_film)

### New Features:
1. **Language-aware duplicate detection** - Never delete only English version
2. **Temp directory staging** - `/volume1/video/duplicates_before_purge/{media_type}/{date}/...`
3. **Deletion reasoning** - Human-readable explanations for every deletion
4. **Manual review flagging** - Uncertain decisions require human approval
5. **Chat with your data** - Azure OpenAI GPT-4o integration with database context

### Decision Rules:
- Keep English audio version over higher-quality non-English (unless foreign film)
- Flag for review if quality difference < 20 points
- Auto-approve if quality difference > 50 points AND language matches
- Never auto-delete foreign films with subtitles
- Track every deletion decision with full reasoning

---

**Next Step:** Review this schema and confirm before I create the SQL migration script!
