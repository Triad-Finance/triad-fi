const express = require("express");
const limitOrderRoutes = require("./routes/limitOrderRoutes");
require("dotenv").config();

const app = express();
app.use(express.json());

app.use("/api", limitOrderRoutes);

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`Server is running on port ${PORT}`);
});
