"""
Analytics & Performance Reporting:
Calculates:
- Win Rate %
- Total P&L (Net of Brokerage, Slippage & Taxes)
- Profit Factor
- Max Drawdown (Rupees & %)
- Risk-Reward Realized
- Kill-Switch trigger stats
Generates Equity Curve visualization chart.
"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os

class PerformanceAnalytics:
    def __init__(self, trades, equity_df, initial_capital=10000.0):
        self.trades_df = pd.DataFrame(trades)
        self.equity_df = equity_df
        self.initial_capital = initial_capital

    def compute_metrics(self) -> dict:
        if self.trades_df.empty:
            return {"error": "No trades executed."}

        total_trades = len(self.trades_df)
        winning_trades = self.trades_df[self.trades_df['net_pnl'] > 0]
        losing_trades = self.trades_df[self.trades_df['net_pnl'] <= 0]
        
        win_count = len(winning_trades)
        loss_count = len(losing_trades)
        win_rate = (win_count / total_trades) * 100 if total_trades > 0 else 0.0

        total_profit = winning_trades['net_pnl'].sum() if win_count > 0 else 0.0
        total_loss = abs(losing_trades['net_pnl'].sum()) if loss_count > 0 else 0.0
        profit_factor = round(total_profit / total_loss, 2) if total_loss > 0 else float('inf')

        net_pnl = round(self.trades_df['net_pnl'].sum(), 2)
        total_costs = round(self.trades_df['costs'].sum(), 2)
        final_capital = self.initial_capital + net_pnl
        return_pct = round((net_pnl / self.initial_capital) * 100, 2)

        avg_win = round(winning_trades['net_pnl'].mean(), 2) if win_count > 0 else 0.0
        avg_loss = round(losing_trades['net_pnl'].mean(), 2) if loss_count > 0 else 0.0

        # Max Drawdown calculation
        equity_series = self.equity_df['capital']
        running_max = equity_series.cummax()
        drawdown_rupees = running_max - equity_series
        max_drawdown_rupees = round(drawdown_rupees.max(), 2)
        max_drawdown_pct = round((drawdown_rupees / running_max).max() * 100, 2)

        # Exit reasons breakdown
        exit_breakdown = self.trades_df['exit_reason'].value_counts().to_dict()

        return {
            "Initial Capital": f"₹{self.initial_capital:,.2f}",
            "Final Capital": f"₹{final_capital:,.2f}",
            "Net P&L": f"₹{net_pnl:,.2f}",
            "Return on Capital (%)": f"{return_pct}%",
            "Total Brokerage & Taxes": f"₹{total_costs:,.2f}",
            "Total Trades": total_trades,
            "Winning Trades": win_count,
            "Losing Trades": loss_count,
            "Win Rate (%)": f"{win_rate:.2f}%",
            "Profit Factor": profit_factor,
            "Avg Win": f"₹{avg_win:,.2f}",
            "Avg Loss": f"₹{avg_loss:,.2f}",
            "Max Drawdown (₹)": f"₹{max_drawdown_rupees:,.2f}",
            "Max Drawdown (%)": f"{max_drawdown_pct:.2f}%",
            "Exit Breakdown": exit_breakdown
        }

    def generate_equity_plot(self, output_path="equity_curve.png"):
        if self.equity_df.empty:
            return None

        plt.figure(figsize=(12, 6))
        plt.plot(self.equity_df['timestamp'], self.equity_df['capital'], label='Portfolio Equity (₹)', color='#10b981', linewidth=1.8)
        plt.axhline(y=self.initial_capital, color='#94a3b8', linestyle='--', label=f'Initial Capital (₹{self.initial_capital:,.0f})')
        
        plt.title('Nifty 50 Options Algo - Equity Curve (1 Lot Intraday with Kill-Switch & 1:2 R:R)', fontsize=13, fontweight='bold')
        plt.xlabel('Date / Time', fontsize=11)
        plt.ylabel('Account Balance (₹)', fontsize=11)
        plt.grid(True, linestyle=':', alpha=0.6)
        plt.legend(loc='upper left')
        plt.tight_layout()
        
        plt.savefig(output_path, dpi=200)
        plt.close()
        return output_path
