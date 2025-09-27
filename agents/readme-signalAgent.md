# Triad DeFi Signal Agent

**Triad DeFi Signal Agent** is a smart **UAgent** designed for the DeFi ecosystem that provides actionable limit order swap recommendations based on Uniswap V4 pool data. It leverages **The Graph API** to fetch on-chain swap data and **OpenAI’s ASI1 Extended model** to generate AI-driven trading signals. This agent is ideal for traders, developers, and DeFi platforms looking to automate their trading strategies and maximize efficiency while minimizing manual intervention.

---

## 🚀 Key Features

- **AI-Driven Limit Order Recommendations:** Predict optimal swap amounts and expiry times using AI models.
- **DeFi Pool Data Integration:** Directly fetches real-time swap data from Uniswap V4 pools using The Graph API.
- **Interval-Based Data Reduction:** Cleans and reduces raw swap data to one representative trade per interval, making AI analysis faster and more accurate.
- **Structured JSON Output:** Returns responses in a strict JSON schema compatible with UAgents, ensuring easy integration into your workflow or platform.
- **User Constraints Enforcement:** Respects user-defined maximum maker amounts and expiry times for limit orders.
- **Highly Configurable:** Supports custom swap intervals, networks (e.g., Polygon), and token limits.
- **Static For Now:** Tracks on Polygon mainnet the WETH/USDTO pool at 0x4ccd010148379ea531d6c587cfdd60180196f9b1 (uniswap v3), latest swaps

---

## 📦 Requirements

- **Python Version:** 3.11+
- **Python Packages:**

```bash
pip install requests uagents pydantic openai
