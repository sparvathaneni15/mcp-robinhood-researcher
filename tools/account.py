import json
from typing import Optional

import robin_stocks.robinhood as rh
from mcp.server.fastmcp import FastMCP


def register_account_tools(mcp: FastMCP) -> None:

    @mcp.tool()
    def get_account_summary() -> str:
        """
        Full account snapshot: account number, account type (margin/cash), equity,
        extended-hours equity, cash, buying power, unsettled funds, and PDT day-trade count.
        Use to check available buying power or PDT proximity before trading.
        """
        account = rh.account.load_account_profile()
        profile = rh.account.load_portfolio_profile()

        if not account:
            return json.dumps({"error": "Could not load account — check authentication"})

        return json.dumps({
            "account_number": account.get("account_number"),
            "type": account.get("type"),
            "equity": (profile or {}).get("equity"),
            "extended_hours_equity": (profile or {}).get("extended_hours_equity"),
            "last_core_equity": (profile or {}).get("last_core_equity"),
            "cash": account.get("cash"),
            "uncleared_deposits": account.get("uncleared_deposits"),
            "unsettled_funds": account.get("unsettled_funds"),
            "buying_power": account.get("buying_power"),
            "sma": account.get("sma"),
            "day_trade_count": account.get("day_trade_count"),
            "pdt_restricted": account.get("only_position_closing_trades", False),
            "created_at": account.get("created_at"),
        }, indent=2)

    @mcp.tool()
    def get_day_trades() -> str:
        """
        Recent day trades with the current PDT day-trade count.
        Robinhood restricts accounts to 3 day trades in a rolling 5-day window
        (Pattern Day Trader rule). Use to monitor PDT compliance.
        """
        account = rh.account.load_account_profile() or {}
        account_number = account.get("account_number")
        trades = rh.account.get_day_trades(account_number) if account_number else []

        return json.dumps({
            "day_trade_count_in_window": account.get("day_trade_count", 0),
            "pdt_threshold": 3,
            "pdt_restricted": account.get("only_position_closing_trades", False),
            "recent_day_trades": trades or [],
        }, indent=2)

    @mcp.tool()
    def get_transfer_history() -> str:
        """
        ACH bank transfer history: deposits and withdrawals with amounts and dates.
        Use for cash flow reconciliation or to confirm a pending deposit cleared.
        """
        data = rh.account.get_bank_transfers() or []
        return json.dumps(data, indent=2)
