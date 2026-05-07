import os
import litellm
from crewai import LLM

litellm.num_retries = 6
litellm.drop_params = True
# Wait for retry-after header (Groq sends exact seconds to wait)
litellm.retry_after = True

llm = LLM(
    model="groq/llama-3.3-70b-versatile",
    # model="gemini/gemini-2.5-flash",
    api_key=os.getenv("GROQ_API_KEY"),
    #api_key=os.getenv("GEMINI_API_KEY"),
    max_retries=6,
    timeout=180,
)
