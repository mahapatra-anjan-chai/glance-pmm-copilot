from google import genai
from google.genai import types
import google.auth
import google.auth.transport.requests
import google.oauth2.credentials
import subprocess
import json, re, sys

# Get a fresh access token from the service account via gcloud
def get_access_token():
    result = subprocess.run(
        ["gcloud", "auth", "print-access-token",
         "--account=ailooks-product-sandbox@glanceai-sandbox-8372.iam.gserviceaccount.com"],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"Failed to get access token: {result.stderr}", file=sys.stderr)
        return None
    return result.stdout.strip()

token = get_access_token()
if not token:
    sys.exit(1)
print(f"Got access token (first 20 chars): {token[:20]}...", file=sys.stderr)

# Use the token to create credentials
creds = google.oauth2.credentials.Credentials(token=token)

client = genai.Client(
    vertexai=True,
    project="glanceai-sandbox-8372",
    location="us-central1",
    credentials=creds,
)

PILLARS = ["The Commerce Shift", "Tech Depth", "Market Intelligence", "Trends & Culture"]

prompt = """
You are a content intelligence analyst. Today is April 28, 2026.

Search the web and find the TOP 5 trending conversations, news stories, or debates happening THIS WEEK (April 21-28, 2026) across these domains:
1. Agentic commerce and AI shopping agents
2. Ambient computing and lockscreen commerce
3. Conversational commerce / AI chat-driven purchases
4. Virtual try-on and AI fashion
5. AI-native retail platforms and their architecture

For each of the 5 trends, provide:
- title: A clear headline describing the trend
- source: Publication or platform name
- url: Source URL if available
- summary: 2-3 sentence summary of what's being discussed and why it matters
- pillar_score: Score 1-10 for relevance to an AI-native agentic commerce platform on Android lockscreens (10 = directly relevant)
- pillar_tag: Which content pillar best fits — one of: "The Commerce Shift", "Tech Depth", "Market Intelligence", "Trends & Culture"
- why_relevant: One sentence on why this matters for a company like Glance (175M device lockscreen commerce platform)

Return ONLY valid JSON array with exactly 5 objects. No markdown, no explanation.
"""

tools = [types.Tool(google_search=types.GoogleSearch())]
config = types.GenerateContentConfig(
    temperature=0.7,
    max_output_tokens=8192,
    tools=tools,
)

models_to_try = ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-2.0-flash-001"]
response_text = None

for model in models_to_try:
    try:
        print(f"Trying model: {model}", file=sys.stderr)
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=config,
        )
        response_text = response.text
        print(f"Success with model: {model}", file=sys.stderr)
        break
    except Exception as e:
        print(f"Model {model} failed: {e}", file=sys.stderr)
        continue

if not response_text:
    print("All models failed", file=sys.stderr)
    sys.exit(1)

# Clean and parse JSON
cleaned = re.sub(r'^```(?:json)?\n?', '', response_text.strip())
cleaned = re.sub(r'\n?```$', '', cleaned)

try:
    trends = json.loads(cleaned)
except json.JSONDecodeError:
    # Try to extract JSON array
    match = re.search(r'\[.*\]', cleaned, re.DOTALL)
    if match:
        trends = json.loads(match.group())
    else:
        print(f"Could not parse JSON from response: {response_text[:500]}", file=sys.stderr)
        sys.exit(1)

output = {"generated_at": "2026-04-28", "trends": trends}
with open("/Users/anjan.mahapatra/Substack/output/trend_scout.json", "w") as f:
    json.dump(output, f, indent=2)

print(json.dumps(output, indent=2))
