require("dotenv").config();
const express = require("express");
const amqp = require("amqplib");

const app = express();
app.use(express.json());

const RABBITMQ_URL = process.env.RABBITMQ_URL;
const EXCHANGE = "topic.exchange";

let channel;

// Connect to RabbitMQ
async function initRabbitMQ() {
  try {
    const connection = await amqp.connect(RABBITMQ_URL);
    channel = await connection.createChannel();

    await channel.assertExchange(EXCHANGE, "topic", { durable: true });

    console.log("Notification Publisher connected to RabbitMQ");
  } catch (err) {
    console.error("RabbitMQ connection failed:", err);
  }
}

app.post("/publish", async (req, res) => {
  try {
    const message = req.body;

    const routingKey = message.notification_type;

    if (!routingKey) {
      return res.status(400).send("Missing notification_type");
    }

    channel.publish(
      EXCHANGE,
      routingKey,
      Buffer.from(JSON.stringify(message)),
      { persistent: true }
    );

    console.log(`Published to ${routingKey}:`, message);

    res.send({ status: "Message published" });

  } catch (err) {
    console.error("Publish error:", err);
    res.status(500).send("Error publishing message");
  }
});


// Start server
const PORT = 3002;

app.listen(PORT, async () => {
  await initRabbitMQ();
  console.log(`Notification Publisher running on port ${PORT}`);
});