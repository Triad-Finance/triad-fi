const oneInchService = require("../services/oneInchService");

async function createLimitOrder(req, res) {
  try {
    // In a real app, you would get these values from req.body
    const orderDetails = {
      makerAsset: "0xc2132d05d31c914a87c6611c10748aeb04b58e8f", // USDT
      takerAsset: "0x7ceb23fd6bc0add59e62ac25578270cff1b9f619", // WETH
      makingAmount: 1_000_000n, // 1 USDT (in 6 decimals)
      takingAmount: 249568300000000n, // 0.0002495683 WETH (18 decimals)
    };

    const result = await oneInchService.createAndSubmitLimitOrder(orderDetails);
    res.status(200).json({ success: true, data: result });
  } catch (error) {
    console.error("Failed to create limit order:", error);
    res.status(500).json({ success: false, message: error.message });
  }
}

module.exports = {
  createLimitOrder,
};
