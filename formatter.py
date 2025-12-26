
"""
Utilities for building nicely‑formatted messages for the Telegram bot.

This module defines a :class:`MessageFormatter` helper that turns raw
token and boost data into human‑readable strings for use in the bot’s
notifications.  All formatting logic is isolated here to keep the
main bot code clean and make unit testing straightforward.

Functions
~~~~~~~~~
* :func:`MessageFormatter.format_price` – Convert a floating point price
  into a string with the appropriate number of decimal places or
  sub‑script notation for very small values.
* :func:`MessageFormatter.format_age` – Translate a pair creation
  timestamp (milliseconds) into a relative age string.
* :func:`MessageFormatter.format_boost_message` – Compose the full
  boost announcement, incorporating market data, transaction statistics,
  platform, and links.

The module relies on the :data:`config.TARGET_CHAIN` constant to build
the DexScreener URL.
"""

import logging
from datetime import datetime
from typing import Optional, Dict
import traceback
from config import TARGET_CHAIN

logger = logging.getLogger(__name__)


class MessageFormatter:
    """
    Helper class that formats various pieces of token and boost data.

    All methods are static as they do not depend on instance state.
    """

    @staticmethod
    def format_price(price_usd: float) -> str:
        """
        Format a USD price with the appropriate precision.

        For very small values the function falls back to a compact
        representation that avoids scientific notation, optionally
        adding subscript zeros to keep the string compact.  Numbers
        larger than or equal to one are shown with up to four decimal
        places, values less than one but greater than 0.001 are shown
        with up to six decimals, and values below 0.001 are formatted
        with up to eight decimals but trimmed of trailing zeros.

        Parameters
        ----------
        price_usd: float
            The price in USD to format.

        Returns
        -------
        str
            The formatted price string, e.g. ``"$12.34"`` or
            ``"$0.00001234"``.
        """
        if price_usd == 0:
            return "$0.00"

        if price_usd < 0.001:
            # For very small prices: use many decimals, strip trailing zeros
            price_str = f"${price_usd:.8f}"
            price_str = price_str.rstrip("0").rstrip(".")

            # Add subscript for extremely small numbers
            if price_usd < 0.000001:
                try:
                    # Attempt to detect scientific notation exponent
                    exp = -int(str(price_usd).split("e-")[-1]) if "e-" in str(price_usd) else 0
                    if exp > 6:
                        base_num = price_usd * (10 ** exp)
                        zeros = "₀" * (exp - 1)
                        return f"$0.{zeros}{base_num:.{min(6, exp)}f}".replace("0.", "")
                except Exception:
                    pass
            return price_str

        if price_usd < 1:
            return f"${price_usd:.6f}".rstrip("0").rstrip(".")

        return f"${price_usd:.4f}".rstrip("0").rstrip(".")

    @staticmethod
    def format_age(pair_created_at: int) -> str:
        """
        Convert a pair creation timestamp into a human‑readable age string.

        Parameters
        ----------
        pair_created_at: int
            Unix timestamp in milliseconds representing when the token
            pair was created.

        Returns
        -------
        str
            A string such as ``"3d 12h"``, ``"5h 30m"``, ``"45m"``, or
            ``"<1m"``.  If the timestamp is missing or invalid, returns
            ``"N/A"``.
        """
        if not pair_created_at:
            return "N/A"

        try:
            created_time = datetime.fromtimestamp(pair_created_at / 1000)
            age_diff = datetime.now() - created_time

            hours = age_diff.seconds // 3600
            minutes = (age_diff.seconds % 3600) // 60

            if age_diff.days > 0:
                return f"{age_diff.days}d {hours}h"
            if hours > 0:
                return f"{hours}h {minutes}m"
            if minutes > 0:
                return f"{minutes}m"
            return "<1m"
        except Exception:
            return "N/A"

    @staticmethod
    def format_boost_message(boost_data: Dict, token_data: Optional[Dict] = None) -> str:
        """
        Build a full boost announcement message from raw data.

        The function pulls the token address, amount, and total amount
        from ``boost_data``.  If ``token_data`` is supplied, it is used
        to enrich the message with the token name, symbol, price,
        market‑cap, liquidity, transaction stats, and age.  Platform
        identification is inferred from the ``dexId`` field.

        Parameters
        ----------
        boost_data: Dict
            Dictionary containing at least ``tokenAddress``,
            ``amount``, and optionally ``totalAmount``.
        token_data: Optional[Dict]
            Dictionary with detailed token information (market data,
            liquidity, transactions).  If omitted, the message will
            contain only minimal information.

        Returns
        -------
        str
            The fully‑formatted markdown message ready to be sent
            via the Telegram bot.  Returns ``None`` if an exception
            occurs during formatting.
        """
        try:
            token_address = boost_data.get("tokenAddress", "Unknown")
            amount = boost_data.get("amount", 0)
            total_amount = boost_data.get("totalAmount", amount)

            # Default placeholders
            token_name = "N/A"
            token_symbol = "N/A"
            price_usd = 0
            market_cap = 0
            liquidity_usd = 0
            age = "N/A"

            buys_5m = sells_5m = buys_24h = sells_24h = 0

            if token_data:
                base_token = token_data.get("baseToken", {})
                token_name = base_token.get("name", "N/A")
                token_symbol = base_token.get("symbol", "N/A")

                price_usd = float(token_data.get("priceUsd", 0))
                market_cap = float(token_data.get("marketCap", 0))
                liquidity = token_data.get("liquidity", {})
                liquidity_usd = float(liquidity.get("usd", 0))

                txns = token_data.get("txns", {})
                buys_5m = txns.get("m5", {}).get("buys", 0)
                sells_5m = txns.get("m5", {}).get("sells", 0)
                buys_24h = txns.get("h24", {}).get("buys", 0)
                sells_24h = txns.get("h24", {}).get("sells", 0)

                pair_created_at = token_data.get("pairCreatedAt")
                age = MessageFormatter.format_age(pair_created_at)

            price_str = MessageFormatter.format_price(price_usd)

            liquidity_percentage = 0
            if market_cap > 0 and liquidity_usd > 0:
                liquidity_percentage = (liquidity_usd / market_cap) * 100

            if token_data:
                dex_id = token_data.get("dexId", "").lower()
                if "pump" in dex_id:
                    platform = "Pump.fun 🔗 SOL"
                elif "raydium" in dex_id:
                    platform = "Raydium 🔗 SOL"
                else:
                    platform = dex_id.capitalize()
            else:
                platform = "Pump.fun 🔗 SOL"

            dexscreener_url = f"https://dexscreener.com/{TARGET_CHAIN}/{token_address}"

            boost_display = f"{amount}⚡ (Total: {total_amount}⚡)" if total_amount > amount else f"{amount}⚡"

            message = f"""
🚨 **DETECTED Boost {boost_display}**

**Token:** {token_name} (${token_symbol})
**CA:** `{token_address}`
**Platform:** {platform}

📊 **Market Data**
• **Age:** {age}
• **Market Cap:** ${market_cap:,.0f}
• **Price:** {price_str}
• **Liquidity:** ${liquidity_usd:,.0f} ({liquidity_percentage:.1f}%)

📈 **Transactions**
• **5m:** {buys_5m} buys | {sells_5m} sells
• **24h:** {buys_24h} buys | {sells_24h} sells

🔗 [DexScreener]({dexscreener_url})
"""

            return message
        except Exception as e:
            logger.error(f"Error formatting message: {e}")

            logger.error(traceback.format_exc())
            return None