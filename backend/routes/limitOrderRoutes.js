const express = require("express");
const { createLimitOrder } = require("../controllers/limitOrderController");

const router = express.Router();

router.post("/limit-order", createLimitOrder);

module.exports = router;
