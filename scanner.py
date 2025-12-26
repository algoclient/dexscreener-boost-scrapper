import requests
import time
import logging
from typing import List, Dict, Optional
from config import BOOST_API_URL, TARGET_CHAIN

logger = logging.getLogger(__name__)

class DexScreenerScanner:
    """
    Scanner that retrieves Solana token boost information from the DexScreener API
    and provides helper methods to fetch detailed token data.
    """

    def __init__(self):
        """
        Initialize a requests.Session with custom headers and an empty cache
        for already processed boost identifiers.
        """
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json'
        })
        self.seen_boost_ids = set()

    def get_boosted_tokens(self) -> List[Dict]:
        """
        Fetch the latest boosted tokens from the DexScreener API, filter them for
        Solana, de-duplicate based on a composite key, and return a list of
        new boost objects.

        Returns:
            List[Dict]: A list of dictionaries representing new Solana boost
            entries. Each dictionary contains the original boost payload.
        """
        try:
            response = self.session.get(BOOST_API_URL, timeout=10)
            response.raise_for_status()
            data = response.json()

            # Normalize the response format to a list of boosts
            if isinstance(data, list):
                boosts = data
            elif isinstance(data, dict) and 'boosts' in data:
                boosts = data['boosts']
            else:
                logger.warning(f"Unexpected API response format: {type(data)}")
                return []

            filtered_boosts: List[Dict] = []
            for boost in boosts:
                chain_id = boost.get('chainId', '').lower()
                if chain_id != TARGET_CHAIN:
                    continue

                # Build a unique identifier for this boost event
                token_address = boost.get('tokenAddress', '')
                amount = boost.get('amount', 0)
                total_amount = boost.get('totalAmount', 0)
                boost_id = f"{token_address}_{amount}_{total_amount}"

                if boost_id in self.seen_boost_ids:
                    continue

                filtered_boosts.append(boost)
                self.seen_boost_ids.add(boost_id)

            logger.info(f"Found {len(filtered_boosts)} new Solana boosts")
            return filtered_boosts

        except Exception as e:
            logger.error(f"Error fetching boosts: {e}")
            return []

    def get_token_details(self, token_address: str) -> Optional[Dict]:
        """
        Retrieve detailed information for a specific Solana token by querying
        DexScreener's search and token endpoints. The function prefers the
        pair with the highest USD liquidity.

        Args:
            token_address (str): The blockchain address of the token.

        Returns:
            Optional[Dict]: A dictionary containing the most liquid Solana pair
            data for the token, or None if no relevant data could be found.
        """
        try:
            # Search endpoint
            search_url = f"https://api.dexscreener.com/latest/dex/search?q={token_address}"
            response = self.session.get(search_url, timeout=5)

            if response.status_code == 200:
                data = response.json()
                if 'pairs' in data and len(data['pairs']) > 0:
                    solana_pairs = [
                        pair for pair in data['pairs']
                        if pair.get('chainId', '').lower() == TARGET_CHAIN
                    ]
                    if solana_pairs:
                        solana_pairs.sort(
                            key=lambda x: float(x.get('liquidity', {}).get('usd', 0)),
                            reverse=True
                        )
                        return solana_pairs[0]

            # Token-specific endpoint fallback
            token_url = f"https://api.dexscreener.com/latest/dex/tokens/{token_address}"
            response = self.session.get(token_url, timeout=5)

            if response.status_code == 200:
                data = response.json()
                if 'pairs' in data and len(data['pairs']) > 0:
                    solana_pairs = [
                        pair for pair in data['pairs']
                        if pair.get('chainId', '').lower() == TARGET_CHAIN
                    ]
                    if solana_pairs:
                        solana_pairs.sort(
                            key=lambda x: float(x.get('liquidity', {}).get('usd', 0)),
                            reverse=True
                        )
                        return solana_pairs[0]

            return None

        except Exception as e:
            logger.error(f"Error fetching token details for {token_address}: {e}")
            return None

    def cleanup_cache(self, max_size: int = 500) -> None:
        """
        Maintain a bounded cache of seen boost identifiers to prevent memory
        growth. If the cache exceeds ``max_size``, it truncates to the most
        recent entries.

        Args:
            max_size (int, optional): Maximum number of identifiers to keep.
                Defaults to 500.
        """
        if len(self.seen_boost_ids) > max_size:
            ids_list = list(self.seen_boost_ids)
            self.seen_boost_ids = set(ids_list[-max_size:])
            logger.info(
                f"Cleaned up boost cache. Now keeping {len(self.seen_boost_ids)} IDs."
            )