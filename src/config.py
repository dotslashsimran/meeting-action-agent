import os
import litellm

litellm.num_retries = 6
litellm.drop_params = True
litellm.retry_after = True
