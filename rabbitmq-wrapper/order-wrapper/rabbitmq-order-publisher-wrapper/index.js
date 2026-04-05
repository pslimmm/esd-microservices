require("dotenv").config();
const express = require("express");
const amqp = require("amqplib");

const app = express();
app.use(express.json());

const PORT = process.env.PORT || 3001;
const RABBITMQ_URL = process.env.RABBITMQ_URL;

const EXCHANGE = "order.exchange"; 

let channel;

// Connect to RabbitMQ
async function connectRabbitMQ() {
  const connection = await amqp.connect(RABBITMQ_URL);
  channel = await connection.createChannel();

  await channel.assertExchange(EXCHANGE, "topic", {
    durable: true,
  });

  console.log("Connected to RabbitMQ");
}

// API endpoint (OutSystems will call this)
app.post("/order-publish", async (req, res) => {
  try {
    const message = req.body;

    console.log("Received from OutSystems:", message);

    const routingKey = "order.created"; // you control this

    channel.publish(
      EXCHANGE,
      routingKey,
      Buffer.from(JSON.stringify(message)),
      { persistent: true }
    );

    console.log("Published to RabbitMQ");

    res.status(200).json({ status: "Message published" });
  } catch (err) {
    console.error("Error publishing:", err);
    res.status(500).json({ error: "Failed to publish" });
  }
});

// Start server
app.listen(PORT, async () => {
  await connectRabbitMQ();
  console.log(`Publisher running on port ${PORT}`);
});