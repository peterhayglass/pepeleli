import asyncio
import json
from typing import Optional, Union

import aiohttp


class VLLMClient:
    def __init__(self, host: str, port: int) -> None:
        self.host = host
        self.port = port
        self.base_uri = f"http://{self.host}:{self.port}"


    async def generate_completion(self, prompt: str, stream: bool = False,
                                   sampling_params: Optional[dict] = None) -> Optional[dict]:
        """Generate AI completion for a given prompt and parameters"""
        if not sampling_params:
            sampling_params = {}

        data = {"prompt": prompt, "stream": stream, **sampling_params}
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{self.base_uri}/generate", json=data) as resp:
                result = await resp.json()

        return result


    async def get_token_usage(self, text: Union[str, list[str]]) -> int:
        """Count how many tokens are used by a given prompt.
        
        Args: 
            text: the text to count tokens for.  Can be a string or a list of strings.

        Returns:
            int: the total number of tokens used by the text
        """
        data = {"prompt": text}
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{self.base_uri}/token_usage", json=data) as resp:
                result = await resp.json()

        return result.get("token_count", 0)