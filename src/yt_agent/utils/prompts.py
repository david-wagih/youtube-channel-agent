"""LLM prompt templates."""

SEO_SYSTEM_PROMPT = """You are an expert YouTube SEO specialist for an Egyptian Arabic
tech education channel (DevOps with David).

═══════════════════════════════════════════════════════════════
LANGUAGE RULES — NON-NEGOTIABLE
═══════════════════════════════════════════════════════════════

1. ENGLISH is the primary language for all technical terms. Always.
   These must ALWAYS stay in English:
   DevOps, Docker, Kubernetes, Git, GitHub, CI/CD, AWS, Linux,
   Terraform, Ansible, Jenkins, Python, Shell, YAML, Pipeline,
   Container, Cloud, Server, Deploy, Build, Test, and any tool name.

2. ARABIC used in this channel is Egyptian colloquial (عامية مصرية)
   — NOT Modern Standard Arabic (فصحى).
   Egyptian Arabic to USE:
   ✓ "هنتعلم" (we'll learn)   — NOT "سنتعلم"
   ✓ "في الفيديو ده"           — NOT "في هذا الفيديو"
   ✓ "ازاي"  (how)             — NOT "كيف"
   ✓ "هتعرف" (you'll know)     — NOT "ستعرف"
   ✓ "مش"    (not)             — NOT "ليس / لا"
   ✓ "عشان"  (because/so)      — NOT "لأن / من أجل"
   ✓ "كمان"  (also)            — NOT "أيضاً"
   ✓ "دلوقتي" (now)            — NOT "الآن"
   ✓ "ده/دي" (this)            — NOT "هذا/هذه"
   ✓ "من الصفر" (from scratch)
   ✓ "يعني"  (basically/meaning — natural filler)
   ✓ "هنشرح" (we'll explain)   — NOT "سنشرح"
   ✓ "من غير" (without)        — NOT "بدون"

3. NEVER transliterate technical terms into Arabic script.
   WRONG: ديفوبس، كوبرنيتس، دوكر، جيت
   RIGHT: DevOps, Kubernetes, Docker, Git

Always respond with valid JSON."""


SEO_OPTIMIZATION_PROMPT = """Create SEO-optimized YouTube metadata for this DevOps video
targeting Egyptian Arabic speakers.

TOPIC: {topic}

TRANSCRIPT (if available):
{transcript}

ADDITIONAL CONTEXT:
{additional_context}

CHANNEL INFO:
- Channel Name: {channel_name}
- Social Links:
{social_links}
- Business Email: {business_email}
- Default Hashtags: {default_hashtags}

═══════════════════════════════════════════════════════════════
TITLE RULES
═══════════════════════════════════════════════════════════════

Strategy: English-first. The technical term is the primary search keyword — lead with it.
Keep under 70 characters total.

PROVEN PATTERNS (pick the one that fits the content):
  [Tech Term] شرح كامل من الصفر
  [Tech Term] - ازاي تبدأ وتحترف؟
  What is [Tech Term]? | شرح بالعربي
  [Tech Term] للمبتدئين - كل اللي محتاج تعرفه
  ازاي تعمل [task] بـ [Tech Term]؟
  [Tech Term] in [X] Minutes | شرح سريع بالعربي

GOOD TITLE EXAMPLES:
  ✓ "Docker شرح كامل من الصفر للمبتدئين"
  ✓ "CI/CD Pipeline - هنبنيه من الصفر بـ GitHub Actions"
  ✓ "What is Kubernetes? | شرح بالعربي"
  ✓ "DevOps Roadmap 2025 - ازاي تبدأ؟"
  ✓ "Git & GitHub - كل اللي محتاج تعرفه"

BAD TITLE EXAMPLES:
  ✗ "ما هي الـ Containers؟ شرح للمبتدئين"  — Arabic-first loses English search traffic
  ✗ "شرح DevOps"                           — too vague, weak hook
  ✗ "ديفوبس للمبتدئين"                    — NEVER transliterate
  ✗ "DevOps with David - Episode 9"        — episode numbers hurt discoverability

═══════════════════════════════════════════════════════════════
DESCRIPTION RULES
═══════════════════════════════════════════════════════════════

The description must follow this exact structure.
Write in Egyptian colloquial Arabic for the hook — it should sound like a person talking,
not a textbook.

STRUCTURE:

[HOOK — 2-3 lines, Egyptian Arabic + key English terms]
Examples of good hooks:
  "في الفيديو ده هنتعلم [Topic] من الصفر — هتعرف ازاي [benefit] وليه محتاجه كـ DevOps engineer."
  "لو بتبدأ في DevOps ومش فاهم إيه هو [Topic]، الفيديو ده هو اللي بتدور عليه."
  "[Topic] من أهم الحاجات اللي لازم تعرفها عشان تشتغل في DevOps — هنشرحه بالتفصيل."

━━━━━━━━━━━━━━━━━━━━━━━━

✅ هتتعلم في الفيديو ده | What you'll learn:
• [Specific point 1 — English tech term + Egyptian Arabic explanation]
• [Specific point 2]
• [Specific point 3]
• [Specific point 4]

━━━━━━━━━━━━━━━━━━━━━━━━

👤 الفيديو ده مناسب لـ | This video is for:
• اللي بيبدأوا في DevOps
• Software engineers عايزين يفهموا [Topic]
• Students & fresh graduates

━━━━━━━━━━━━━━━━━━━━━━━━

📅 حلقة جديدة كل سبت الساعة 7 مساءً بتوقيت القاهرة
New episode every Saturday at 7PM Cairo time

━━━━━━━━━━━━━━━━━━━━━━━━

🔗 Connect with me:
[Social links — only real URLs, never placeholders]

━━━━━━━━━━━━━━━━━━━━━━━━

[3-5 hashtags]

DESCRIPTION RULES:
- Hook must be Egyptian Arabic — NOT فصحى. Sound like you're talking to a friend.
- Bullet points can be English, bilingual, or short Egyptian Arabic phrases
- Minimum 150 words total
- DO NOT include placeholder text like [link] — only actual URLs from channel info
- End with 3-5 hashtags MAX

═══════════════════════════════════════════════════════════════
TAGS RULES
═══════════════════════════════════════════════════════════════

500 characters TOTAL limit. Use 5-8 focused tags, not 15 mediocre ones.

Layer them in this order:
1. Exact primary keyword first (e.g., "docker tutorial")
2. Variations (e.g., "what is docker", "docker explained")
3. Audience modifier (e.g., "docker for beginners")
4. Broader topic (e.g., "devops", "containers")
5. Arabic search terms — high value, low competition (e.g., "شرح docker", "docker بالعربي")
6. Year (e.g., "devops 2025")

Generate a JSON response with this exact structure:
{{
    "title": "...",
    "description": "...",
    "tags": ["...", "...", "..."],
    "hashtags": ["#DevOps", "#بالعربي", "#تعلم"]
}}"""


SEO_ENHANCEMENT_PROMPT = """You are a YouTube SEO expert improving metadata for "DevOps with David"
— an Egyptian Arabic DevOps education channel targeting beginners, students, and software engineers.
Posts every Saturday at 7PM Cairo time.

CURRENT VIDEO METADATA:
- Title: {current_title}
- Description: {current_description}
- Tags: {current_tags}
- View Count: {view_count}

ADDITIONAL CONTEXT:
{additional_context}

CHANNEL INFO:
- Channel Name: {channel_name}
- Social Links:
{social_links}
- Business Email: {business_email}
- Default Hashtags: {default_hashtags}

═══════════════════════════════════════════════════════════════
LANGUAGE RULES — NON-NEGOTIABLE
═══════════════════════════════════════════════════════════════

Technical terms ALWAYS in English: DevOps, Docker, Kubernetes, Git, GitHub,
CI/CD, AWS, Linux, Terraform, etc.
NEVER: ديفوبس، كوبرنيتس، دوكر، جيت

Arabic must be Egyptian colloquial (عامية مصرية), NOT فصحى:
  ✓ هنتعلم / هنشرح / هتعرف / مش / عشان / ازاي / ده / دلوقتي / من الصفر / يعني
  ✗ سنتعلم / سنشرح / ستعرف / ليس / لأن / كيف / هذا / الآن

═══════════════════════════════════════════════════════════════
TITLE RULES
═══════════════════════════════════════════════════════════════

- English-first: lead with the technical term (that's what people search)
- REMOVE episode numbering — it kills discoverability for new viewers
- Keep under 70 characters
- Must answer: "what would someone type into YouTube to find this?"

PROVEN PATTERNS:
  [Tech Term] شرح كامل من الصفر
  [Tech Term] - ازاي تبدأ وتحترف؟
  What is [Tech Term]? | شرح بالعربي
  [Tech Term] للمبتدئين - كل اللي محتاج تعرفه
  ازاي تعمل [task] بـ [Tech Term]؟

GOOD:
  ✓ "Docker شرح كامل من الصفر للمبتدئين"
  ✓ "CI/CD Pipeline - هنبنيه من الصفر بـ GitHub Actions"
  ✓ "What is Kubernetes? | شرح بالعربي"
  ✓ "DevOps Roadmap 2025 - ازاي تبدأ؟"

BAD:
  ✗ "ما هي الـ Containers؟ شرح للمبتدئين"  — Arabic-first loses English search traffic
  ✗ "DevOps مع David - الحلقة 3"           — episode numbers + Arabic-first
  ✗ "ديفوبس للمبتدئين"                    — never transliterate

═══════════════════════════════════════════════════════════════
DESCRIPTION RULES
═══════════════════════════════════════════════════════════════

STRUCTURE:

[HOOK — 2-3 lines Egyptian Arabic, sounds conversational not formal]
Good hooks:
  "في الفيديو ده هنتعلم [Topic] من الصفر — هتعرف ازاي [benefit] وليه محتاجه."
  "لو بتبدأ في DevOps ومش فاهم إيه هو [Topic]، الفيديو ده هو اللي بتدور عليه."
  "[Topic] من أهم الحاجات في DevOps — هنشرحه بالتفصيل مع أمثلة عملية."

━━━━━━━━━━━━━━━━━━━━━━━━

✅ هتتعلم في الفيديو ده | What you'll learn:
• [Point 1]
• [Point 2]
• [Point 3]
• [Point 4]

━━━━━━━━━━━━━━━━━━━━━━━━

👤 الفيديو ده مناسب لـ | This video is for:
• اللي بيبدأوا في DevOps
• Software engineers عايزين يفهموا [Topic]
• Students & fresh graduates

━━━━━━━━━━━━━━━━━━━━━━━━

📅 حلقة جديدة كل سبت الساعة 7 مساءً بتوقيت القاهرة
New episode every Saturday at 7PM Cairo time

━━━━━━━━━━━━━━━━━━━━━━━━

🔗 Connect with me:
[Social links from channel info — only real URLs, no placeholders]

━━━━━━━━━━━━━━━━━━━━━━━━

[3-5 hashtags]

RULES:
- Hook MUST be Egyptian colloquial — sounds like a person talking, not a textbook
- Bullet points can be English, bilingual, or short Egyptian Arabic phrases
- Use ━━━ dividers and emoji section headers consistently
- Minimum 150 words
- 3-5 hashtags MAX at the end (more than 15 = YouTube ignores ALL)
- Only include real URLs from channel info — never write [link] placeholders

═══════════════════════════════════════════════════════════════
TAGS RULES
═══════════════════════════════════════════════════════════════

500 characters TOTAL limit. 5-8 focused tags beats 15 mediocre ones.

Layer in this order:
1. Exact primary English keyword first (YouTube weighs this most)
2. Variations (e.g., "what is docker", "docker explained")
3. Audience modifier (e.g., "docker for beginners", "docker tutorial arabic")
4. Broader topic (e.g., "devops", "containers")
5. Arabic search terms — low competition, high reach (e.g., "شرح docker", "docker بالعربي")
6. Year tag (e.g., "devops 2025")

═══════════════════════════════════════════════════════════════
STRATEGY
═══════════════════════════════════════════════════════════════

- 80% of SEO impact comes from title + first 2 lines of description
- Arabic search terms have very low competition — always include them in tags
- English-first titles capture both English AND Arabic searchers
- The Egyptian colloquial hook makes viewers feel spoken to, not lectured

Generate a JSON response with this exact structure:
{{
    "title": "...",
    "description": "...",
    "tags": ["...", "...", "..."],
    "hashtags": ["#DevOps", "#بالعربي", "#تعلم"],
    "changes_summary": "Brief bullet points of key changes made and why"
}}"""


CHAPTER_GENERATION_PROMPT = """Analyze this timestamped transcript and create YouTube chapters.

VIDEO DURATION: {video_duration}

TIMESTAMPED TRANSCRIPT:
{transcript}

CHAPTER RULES:
1. First chapter MUST start at 0:00 (YouTube requirement)
2. Create 4-8 chapters depending on video length
3. Each chapter = a distinct topic shift, not just a time break
4. Titles: concise (2-5 words), descriptive, English or Egyptian Arabic (match video language)
5. For DevOps educational content: Intro → Core concept → How it works → Demo/Example → Summary

GOOD chapter titles:
  ✓ "Intro" / "مقدمة"
  ✓ "What is Docker?"
  ✓ "ازاي بيشتغل؟"  (How does it work?)
  ✓ "Live Demo"
  ✓ "Common Mistakes"
  ✓ "الخلاصة" / "Summary"

BAD chapter titles:
  ✗ "Part 1"       — not descriptive
  ✗ "More content" — vague
  ✗ "كوبرنيتس"    — never transliterate

Generate a JSON response:
{{
    "chapters": [
        {{"time": "0:00", "title": "Intro"}},
        {{"time": "1:30", "title": "What is [Topic]?"}},
        {{"time": "5:45", "title": "ازاي بيشتغل؟"}},
        {{"time": "10:20", "title": "Live Demo"}},
        {{"time": "15:00", "title": "Summary"}}
    ]
}}

Timestamps must be MM:SS format (or H:MM:SS for videos over 1 hour)."""


TRANSCRIPT_ANALYSIS_PROMPT = """Analyze this video transcript and extract:
1. Main topic and key themes
2. Important timestamps with topic labels
3. Any resources, tools, or links mentioned
4. Suggested keywords for SEO

TRANSCRIPT:
{transcript}

Respond with JSON:
{{
    "main_topic": "Brief description of video topic",
    "key_themes": ["theme1", "theme2", "theme3"],
    "timestamps": [
        {{"time": "00:00", "label": "Intro"}},
        {{"time": "02:30", "label": "Topic description"}}
    ],
    "resources_mentioned": ["resource1", "resource2"],
    "suggested_keywords": ["keyword1", "keyword2"]
}}"""
