require("dotenv").config();
const express = require("express");
const amqp = require("amqplib");

const app = express();
app.use(express.json());

const RABBITMQ_URL = process.env.PUBLISHER_RABBITMQ_URL;
const EXCHANGE = "topic.exchange";
const NOTIFICATION_ROUTING_KEY = ".notification";
const PORT = process.env.PUBLISHER_PORT;

let conn;
let channel;
let server;

async function initRabbit() {
  conn = await amqp.connect(RABBITMQ_URL);
  
  // BEST PRACTICE: Use a ConfirmChannel. This allows us to wait for the broker 
  // to acknowledge that the message was safely written to disk.
  channel = await conn.createConfirmChannel();

  // Handle unexpected connection drops
  conn.on("error", (err) => console.error("❌ RabbitMQ Connection Error:", err));
  conn.on("close", () => {
    console.error("❌ RabbitMQ Connection Closed. Exiting...");
    process.exit(1);
  });

  await channel.assertExchange(EXCHANGE, "topic", { durable: true });
  console.log("✅ Publisher connected to RabbitMQ");
}

app.post("/notification-publish", async (req, res) => {
  try {
    // Basic safety check
    if (!channel) {
      return res.status(503).send({ error: "RabbitMQ channel is not ready" });
    }

    const message = req.body;
    const content = Buffer.from(JSON.stringify(message));

    // BEST PRACTICE: Wrap the publish event in a Promise using the callback provided 
    // by ConfirmChannel. This guarantees we only respond to the HTTP client 
    // AFTER RabbitMQ has safely accepted the message.
    await new Promise((resolve, reject) => {
      channel.publish(
        EXCHANGE,
        message.notification_type + NOTIFICATION_ROUTING_KEY,
        content,
        { persistent: true },
        (err, ok) => {
          if (err) {
            console.error("❌ Broker rejected message:", err);
            reject(err);
          } else {
            resolve(ok);
          }
        }
      );
    });

    console.log("📤 Published and Confirmed:", message);
    res.status(200).send({ status: "Message published safely" });

  } catch (err) {
    console.error("❌ Error publishing:", err.message);
    res.status(500).send({ error: "Failed to publish message" });
  }
});

// BEST PRACTICE: Ensure RabbitMQ is connected BEFORE accepting HTTP traffic.
async function startServer() {
  try {
    await initRabbit();
    server = app.listen(PORT, () => {
      console.log(`🚀 Publisher API running on port ${PORT}`);
    });
  } catch (err) {
    console.error("❌ Failed to start application:", err.message);
    process.exit(1);
  }
}

// BEST PRACTICE: Graceful shutdown to finish active HTTP requests and close AMQP
async function shutdown() {
  console.log("\n🛑 Shutting down gracefully...");
  
  if (server) {
    server.close(() => console.log("✅ Express server closed."));
  }

  try {
    if (channel) await channel.close();
    if (conn) await conn.close();
    console.log("✅ RabbitMQ connection closed.");
    process.exit(0);
  } catch (err) {
    console.error("❌ Error during shutdown:", err);
    process.exit(1);
  }
}

process.on("SIGINT", shutdown);
process.on("SIGTERM", shutdown);

startServer();