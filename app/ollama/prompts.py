stock_positions_summary = """
You are a financial analyst and an expert in investment portfolio management.

Based on the provided stock portfolio data, please:

1. Write a brief summary of the portfolio structure:
   - Which stocks represent the largest portions.
   - Which sectors are dominant.
   - How well the portfolio is diversified.

2. Provide recommendations:
   - How diversification can be improved.
   - What potential risks should be considered.
   - Whether the asset balance needs adjustment.

Portfolio data:

{stock_positions}

Instructions:
- Keep the response concise (no more than 300 words).
- Write in English.
- Avoid unnecessary details about individual companies.
- Focus on the overall portfolio structure and investment strategy.
"""
