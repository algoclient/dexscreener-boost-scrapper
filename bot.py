# TelegramBot/bot.py

import asyncio
import logging
from telegram import Bot
from telegram.constants import ParseMode

from config import (
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHAT_ID,
    SCAN_INTERVAL,
    BOOST_AMOUNTS,
    CACHE_CLEANUP_INTERVAL,
)
from scanner import DexScreenerScanner
from formatter import MessageFormatter

# --------------------------------------------------------------------------- #
# Logging configuration
# --------------------------------------------------------------------------- #
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------- #
# DexBoostBot
# --------------------------------------------------------------------------- #
class DexBoostBot:
    """
    Bot that watches DexScreener for “boost” events and posts formatted
    alerts to a Telegram chat.

    The bot periodically scans for new boosts, filters them by a set of
    target amounts, formats a message, and sends it to Telegram.  It
    also keeps per‑amount statistics and performs cache clean‑up on
    a configurable schedule.
    """

    def __init__(self):
        """
        Initialise the bot.

        * Create a :class:`telegram.Bot` instance using the configured token.
        * Instantiate the scanner and formatter helpers.
        * Build a statistics dictionary keyed by the target boost amounts.
        """
        self.bot = Bot(token=TELEGRAM_BOT_TOKEN)
        self.scanner = DexScreenerScanner()
        self.formatter = MessageFormatter()
        self.boost_stats = {amount: 0 for amount in BOOST_AMOUNTS}

        logger.info("🤖 DexScreener Boost Bot Initialized")
        logger.info(f"Monitoring boost amounts: {BOOST_AMOUNTS}")

    # --------------------------------------------------------------------- #
    # Helper methods
    # --------------------------------------------------------------------- #
    def check_boost_criteria(self, boost_data):
        """
        Return ``True`` if the boost amount is one of the target amounts.

        Parameters
        ----------
        boost_data : dict
            The raw boost payload from DexScreener.

        Returns
        -------
        bool
            ``True`` if ``boost_data['amount']`` is in ``BOOST_AMOUNTS``.
        """
        amount = boost_data.get("amount", 0)
        return amount in BOOST_AMOUNTS

    async def send_alert(self, message):
        """
        Send a single alert message to Telegram.

        The message is sent using Markdown formatting and will *not*
        suppress web‑page previews.

        Parameters
        ----------
        message : str
            The formatted message to send.

        Returns
        -------
        bool
            ``True`` if the message was sent successfully,
            ``False`` otherwise (logged internally).
        """
        try:
            await self.bot.send_message(
                chat_id=TELEGRAM_CHAT_ID,
                text=message,
                parse_mode=ParseMode.MARKDOWN,
                disable_web_page_preview=False,
            )
            return True
        except Exception as e:
            logger.error(f"Failed to send alert: {e}")
            return False

    async def process_boost(self, boost):
        """
        Process a single boost event and send an alert if appropriate.

        The workflow is:

        1. Extract the token address and amount.
        2. Retrieve cached token metadata.
        3. Format the alert text.
        4. Send the alert.
        5. Update statistics.

        Parameters
        ----------
        boost : dict
            The boost record from DexScreener.

        Returns
        -------
        bool
            ``True`` if an alert was sent, ``False`` otherwise.
        """
        try:
            token_address = boost.get("tokenAddress")
            amount = boost.get("amount", 0)

            logger.info(f"Processing {amount}⚡ boost for {token_address}")

            # Get token details (may hit cache or API)
            token_data = self.scanner.get_token_details(token_address)

            # Format the message that will be sent
            message = self.formatter.format_boost_message(boost, token_data)

            if not message:
                logger.warning(f"Could not format message for {token_address}")
                return False

            # Send the alert
            success = await self.send_alert(message)

            if success:
                self.boost_stats[amount] += 1
                logger.info(f"✅ Alert sent for {amount}⚡ boost")
                return True

            return False

        except Exception as e:
            logger.error(f"Error processing boost: {e}")
            return False

    async def scan_and_process(self):
        """
        Perform one scan cycle: fetch new boosts, filter, and process them.

        Returns
        -------
        int
            Number of boosts that successfully triggered an alert.
        """
        logger.info("🔍 Scanning for new boosts...")

        # Retrieve raw boost data
        boosts = self.scanner.get_boosted_tokens()

        if not boosts:
            logger.info("No new boosts found")
            return 0

        # Keep only boosts that match the target amounts
        target_boosts = [b for b in boosts if self.check_boost_criteria(b)]

        if not target_boosts:
            logger.info("No boosts matching target amounts")
            return 0

        logger.info(f"Found {len(target_boosts)} matching boosts")

        # Process each matching boost sequentially
        processed_count = 0
        for boost in target_boosts:
            success = await self.process_boost(boost)
            if success:
                processed_count += 1
                await asyncio.sleep(1)  # brief pause between messages

        return processed_count

    # --------------------------------------------------------------------- #
    # Main loop
    # --------------------------------------------------------------------- #
    async def run(self):
        """
        Main event loop of the bot.

        It repeatedly:

        1. Sends a startup message.
        2. Scans and processes boosts.
        3. Logs a summary.
        4. Performs periodic cache cleanup.
        5. Sleeps for :data:`SCAN_INTERVAL` seconds.

        On shutdown (KeyboardInterrupt or exception), a final
        statistics message is sent before the process exits.
        """
        logger.info("🚀 Starting DexScreener Boost Bot...")

        # Startup notification
        try:
            startup_msg = (
                "🤖 **DexScreener Boost Bot Started!**\n\n"
                f"**Monitoring:** {', '.join(str(a) + '⚡' for a in BOOST_AMOUNTS)}\n"
                f"**Scan Interval:** {SCAN_INTERVAL} seconds\n\n"
                "Standing by for boost purchases... ⚡"
            )

            await self.bot.send_message(
                chat_id=TELEGRAM_CHAT_ID,
                text=startup_msg,
                parse_mode=ParseMode.MARKDOWN,
            )
            logger.info("✅ Startup message sent")
        except Exception as e:
            logger.error(f"Failed to send startup message: {e}")

        # Loop variables
        scan_count = 0
        total_alerts = 0

        try:
            while True:
                scan_count += 1

                # Execute a scan cycle
                alerts_sent = await self.scan_and_process()
                total_alerts += alerts_sent

                # Log per‑cycle stats
                if alerts_sent > 0:
                    logger.info(f"Scan #{scan_count}: {alerts_sent} alerts sent")
                    logger.info(f"Total alerts: {total_alerts}")
                    logger.info(f"Stats: {self.boost_stats}")

                # Periodic cache cleanup
                if scan_count % CACHE_CLEANUP_INTERVAL == 0:
                    self.scanner.cleanup_cache()

                # Wait before the next cycle
                await asyncio.sleep(SCAN_INTERVAL)

        except KeyboardInterrupt:
            logger.info("\n👋 Received KeyboardInterrupt")
        except Exception as e:
            logger.error(f"Unexpected error in main loop: {e}")
            import traceback

            logger.error(traceback.format_exc())

        # Shutdown notification
        try:
            shutdown_msg = (
                "🤖 **DexScreener Boost Bot Stopped**\n\n"
                f"**Final Statistics:**\n"
                f"• Total scans: {scan_count}\n"
                f"• Total alerts: {total_alerts}\n"
                f"• Boost breakdown: {self.boost_stats}\n\n"
                "Bot has been shut down. 👋"
            )

            await self.bot.send_message(
                chat_id=TELEGRAM_CHAT_ID,
                text=shutdown_msg,
                parse_mode=ParseMode.MARKDOWN,
            )
            logger.info("✅ Shutdown message sent")
        except Exception as e:
            logger.error(f"Failed to send shutdown message: {e}")

        logger.info("Bot stopped gracefully")

# --------------------------------------------------------------------------- #
# Entry point
# --------------------------------------------------------------------------- #
async def main():
    """
    Bootstrap the bot, ensuring a Windows‑compatible event loop
    policy on Windows platforms.
    """
    bot = DexBoostBot()

    # Windows compatibility
    if hasattr(asyncio, "WindowsSelectorEventLoopPolicy"):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    await bot.run()


# --------------------------------------------------------------------------- #
# CLI execution
# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    print("=" * 50)
    print("🤖 DEXSCREENER BOOST BOT")
    print("=" * 50)
    print(f"Monitoring boost amounts: {BOOST_AMOUNTS}")
    print(f"Scan interval: {SCAN_INTERVAL} seconds")
    print("=" * 50)
    print("Starting bot... (Press Ctrl+C to stop)")
    print("=" * 50)

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Bot stopped by user")
    except Exception as e:
        print(f"\n❌ Bot crashed: {e}")
        import traceback

        traceback.print_exc()