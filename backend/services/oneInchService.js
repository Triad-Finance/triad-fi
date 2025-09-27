const { Wallet, JsonRpcProvider, Contract } = require("ethers");
const {
  Sdk,
  MakerTraits,
  Address,
  randBigInt,
  FetchProviderConnector,
  getLimitOrderV4Domain,
} = require("@1inch/limit-order-sdk");

// Standard ERC-20 ABI fragment (used for token approval)
const erc20AbiFragment = [
  "function approve(address spender, uint256 amount) external returns (bool)",
  "function allowance(address owner, address spender) external view returns (uint256)",
];

async function createAndSubmitLimitOrder({
  makerAsset,
  takerAsset,
  makingAmount,
  takingAmount,
}) {
  const privKey = process.env.PRIVATE_KEY;
  const authKey = process.env["1INCH_API_KEY"];
  const chainId = 137; // Polygon mainnet

  const provider = new JsonRpcProvider(
    "https://polygon-mainnet.g.alchemy.com/v2/Rtw4vwfxxDHm3CwVLcGzi-XA4KOtc159"
  );
  const wallet = new Wallet(privKey, provider);

  const expiresIn = 120n; // seconds
  const expiration = BigInt(Math.floor(Date.now() / 1000)) + expiresIn;

  // Check the current allowance, and if it’s insufficient, approve the required amount:
  const domain = getLimitOrderV4Domain(chainId);
  const limitOrderContractAddress = domain.verifyingContract;

  const makerAssetContract = new Contract(makerAsset, erc20AbiFragment, wallet);

  const currentAllowance = await makerAssetContract.allowance(
    wallet.address,
    limitOrderContractAddress
  );

  if (currentAllowance < makingAmount) {
    const approveTx = await makerAssetContract.approve(
      limitOrderContractAddress,
      makingAmount
    );
    await approveTx.wait();
  }

  // Initialize the SDK and create MakerTraits
  const sdk = new Sdk({
    authKey,
    networkId: chainId,
    httpConnector: new FetchProviderConnector(),
  });
  const UINT_40_MAX = (1n << 32n) - 1n;

  const makerTraits = MakerTraits.default()
    .withExpiration(expiration)
    .withNonce(randBigInt(UINT_40_MAX))
    .allowPartialFills()
    .allowMultipleFills();

  // Create the limit order
  const order = await sdk.createOrder(
    {
      makerAsset: new Address(makerAsset),
      takerAsset: new Address(takerAsset),
      makingAmount,
      takingAmount,
      maker: new Address(wallet.address),
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
  const result = await sdk.submitOrder(order, signature);
  console.log("Order submitted successfully:", result);
  return result;
}

module.exports = {
  createAndSubmitLimitOrder,
};
