# Triad Finance - Agentic Finance for Financial Institutions

## Overview

Triad Finance is a DeFi platform that enables financial institutions to interact with decentralized protocols through automated agents. The backend implements 1inch limit order functionality for creating and managing limit orders on Polygon network.

## Backend

The backend is a Node.js application that integrates with the 1inch Limit Order Protocol SDK to create, sign, and submit limit orders on the Polygon network.

### Features

- **1inch Limit Order Integration**: Create and submit limit orders using the 1inch Limit Order Protocol
- **ERC-20 Token Support**: Handle token approvals and allowances
- **Polygon Network**: Configured for Polygon mainnet with Alchemy RPC provider
- **Wallet Management**: Secure wallet integration using ethers.js
- **Environment Configuration**: Secure handling of private keys and API keys

### Project Structure

```
backend/
├── limit-order-sdk.js     # Main application file with limit order logic
├── package.json           # Node.js dependencies and scripts
├── 1inch-tokens.json      # Token configuration file
├── .env.example          # Environment variables template
├── .env                  # Environment variables (not tracked in git)
└── .gitignore           # Git ignore rules
```

### Dependencies

- **@1inch/limit-order-sdk**: 1inch Limit Order Protocol SDK
- **ethers**: Ethereum library for wallet and contract interactions
- **dotenv**: Environment variable management

### Setup and Installation

1. **Clone the repository**

   ```bash
   git clone https://github.com/Triad-Finance/triad-fi.git
   cd triad-fi/backend
   ```

2. **Install dependencies**

   ```bash
   npm install
   ```

3. **Configure environment variables**

   ```bash
   cp .env.example .env
   ```

   Edit `.env` and add your credentials:

   ```bash
   PRIVATE_KEY=your_wallet_private_key
   ALCHEMY_URL=https://polygon-mainnet.g.alchemy.com/v2/your_alchemy_api_key
   1INCH_API_KEY=your_1inch_api_key
   ```

4. **Run the application**
   ```bash
   npm start
   ```

### Configuration

The application is pre-configured with:

- **Network**: Polygon Mainnet (Chain ID: 137)
- **Maker Asset**: USDT (0xc2132d05d31c914a87c6611c10748aeb04b58e8f)
- **Taker Asset**: WETH (0x7ceb23fd6bc0add59e62ac25578270cff1b9f619)
- **Order Expiration**: 120 seconds
- **Partial Fills**: Enabled
- **Multiple Fills**: Enabled

### How It Works

1. **Token Approval**: Checks and approves token allowance for the 1inch limit order contract
2. **Order Creation**: Creates a limit order with specified maker/taker assets and amounts
3. **Order Signing**: Signs the order using the wallet's private key
4. **Order Submission**: Submits the signed order to the 1inch API

### API Keys Required

- **1inch API Key**: Get from [1inch Developer Portal](https://developers.1inch.io/)
- **Alchemy API Key**: Get from [Alchemy Dashboard](https://dashboard.alchemy.com/)
- **Wallet Private Key**: Your Ethereum wallet private key (keep secure!)

### Security Notes

- Never commit your `.env` file to version control
- Keep your private keys secure and never share them
- Use environment variables for all sensitive configuration
- Consider using hardware wallets for production deployments

### Example Order

The current configuration creates a limit order to:

- **Sell**: 1 USDT (1,000,000 units with 6 decimals)
- **Buy**: 0.0002495683 WETH (249,568,300,000,000 units with 18 decimals)
- **Expires**: In 120 seconds from creation

### Development

To modify the order parameters, edit the values in `limit-order-sdk.js`:

```javascript
const makingAmount = 1_000_000n; // Amount to sell
const takingAmount = 249568300000000n; // Amount to receive
const expiresIn = 120n; // Expiration time in seconds
```
