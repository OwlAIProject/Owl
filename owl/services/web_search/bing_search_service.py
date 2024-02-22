import httpx
from ...models.bing import BingSearchResponse
from ...core.config import BingConfiguration

class BingSearchService:
    def __init__(self, config: BingConfiguration):
        self._config = config
        self._base_url = "https://api.bing.microsoft.com/v7.0/search"
        self._headers = {"Ocp-Apim-Subscription-Key": self._config.subscription_key}

    async def search(self, query: str) -> BingSearchResponse:
        async with httpx.AsyncClient() as client:
            params = {"q": query}
            response = await client.get(self._base_url, headers=self._headers, params=params)
            response.raise_for_status()  
            return BingSearchResponse(**response.json())