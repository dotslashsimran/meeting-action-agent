import litellm
from crewai import LLM

# Global litellm retry settings — ensures rate-limit responses trigger
# exponential backoff before re-attempting.
litellm.num_retries = 10
litellm.drop_params = True

# llama-4-scout is a newer model on Groq with higher free-tier rate limits
# than the older llama-3.x models.
llm = LLM(
    model="groq/meta-llama/llama-4-scout-17b-16e-instruct",
    max_retries=10,
    timeout=120,
)
