const { Wallet, JsonRpcProvider, Contract, MaxUint256 } = require("ethers");
const {
  Sdk,
  MakerTraits,
  Address,
  randBigInt,
  FetchProviderConnector,
  getLimitOrderV4Domain,
} = require("@1inch/limit-order-sdk");
require("dotenv").config();

// Standard ERC-20 ABI fragment (used for token approval)
const erc20AbiFragment = [
  "function approve(address spender, uint256 amount) external returns (bool)",
  "function allowance(address owner, address spender) external view returns (uint256)",
];

async function main() {
  const privKey = process.env.PRIVATE_KEY;
  const authKey = process.env["1INCH_API_KEY"];
  const chainId = 137; // Polygon mainnet

  const provider = new JsonRpcProvider(
    "https://polygon-mainnet.g.alchemy.com/v2/Rtw4vwfxxDHm3CwVLcGzi-XA4KOtc159"
  );
  const wallet = new Wallet(privKey, provider);

  console.log("Here 1");

  const makerAsset = "0xc2132d05d31c914a87c6611c10748aeb04b58e8f"; // USDT
  const takerAsset = "0x7ceb23fd6bc0add59e62ac25578270cff1b9f619"; // WETH

  const makingAmount = 1_000_000n; // 1 USDT (in 6 decimals)
  // const takingAmount = 1_000_000_000_000_000_000n; // 1 WETH (18 decimals)
  const takingAmount = 249568300000000n; // 0.0002495683 WETH (18 decimals)

  const expiresIn = 120n; // seconds
  const expiration = BigInt(Math.floor(Date.now() / 1000)) + expiresIn;

  // Check the current allowance, and if it’s insufficient, approve the required amount:

  const domain = getLimitOrderV4Domain(chainId);
  const limitOrderContractAddress = domain.verifyingContract;
  console.log("Here 2");

  const makerAssetContract = new Contract(makerAsset, erc20AbiFragment, wallet);

  const currentAllowance = await makerAssetContract.allowance(
    wallet.address,
    limitOrderContractAddress
  );

  if (currentAllowance < makingAmount) {
    // Approve just the necessary amount or the full MaxUint256 to avoid repeated approvals
    const approveTx = await makerAssetContract.approve(
      limitOrderContractAddress,
      makingAmount
    );
    await approveTx.wait();
  }

  console.log("Here 3");

  // Initialize the SDK and create MakerTraits

  const sdk = new Sdk({
    authKey,
    networkId: chainId,
    httpConnector: new FetchProviderConnector(),
  });
  const UINT_40_MAX = (1n << 32n) - 1n;

  console.log("Here 4");

  const makerTraits = MakerTraits.default()
    .withExpiration(expiration)
    .withNonce(randBigInt(UINT_40_MAX))
    .allowPartialFills()
    .allowMultipleFills();

  console.log("Here 5");

  // Create the limit order
  const order = await sdk.createOrder(
    {
      makerAsset: new Address(makerAsset),
      takerAsset: new Address(takerAsset),
      makingAmount,
      takingAmount,
      maker: new Address(wallet.address),
      // receiver: new Address(wallet.address), // Optional - defaults to maker
      // salt: randBigInt(UINT_40_MAX), // Optional - auto-generated if not provided
    },
    makerTraits
  );
  console.log("Order created:", order);

  // Sign the order
  const typedData = order.getTypedData(chainId);

  const signature = await wallet.signTypedData(
    typedData.domain,
    { Order: typedData.types[typedData.primaryType] },
    typedData.message
  );

  // Submit the order to 1inch API
  try {
    const result = await sdk.submitOrder(order, signature);
    console.log("Order submitted successfully:", result);
  } catch (error) {
    console.error("Failed to submit order:", error);
  }
}

main();
