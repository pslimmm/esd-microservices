require("dotenv").config();
const amqp = require("amqplib");
const axios = require("axios");

const RABBITMQ_URL = process.env.RABBITMQ_URL;
const QUEUE = process.env.QUEUE_NAME;
const EXCHANGE = "topic.exchange";
const ROUTING_KEY = "arrival";
const API = process.env.API;

let conn;
let channel;

async function startConsumer() {
  try {
    conn = await amqp.connect(RABBITMQ_URL);
    channel = await conn.createChannel();

    // Handle unexpected connection drops
    conn.on("error", (err) => console.error("❌ RabbitMQ Connection Error:", err));
    conn.on("close", () => {
      console.error("❌ RabbitMQ Connection Closed. Exiting...");
      process.exit(1); // Exit to allow process manager (like PM2/Docker) to restart
    });

    await channel.assertExchange(EXCHANGE, "topic", { durable: true });
    await channel.assertQueue(QUEUE, { durable: true });
    await channel.bindQueue(QUEUE, EXCHANGE, ROUTING_KEY);

    // BEST PRACTICE: Limit unacked messages to prevent memory overload
    await channel.prefetch(10); 

    console.log("📥 Waiting for messages...");

    channel.consume(QUEUE, async (msg) => {
      if (!msg) return;

      let data;
      
      // BEST PRACTICE: Safely parse JSON to prevent crashes from malformed payloads
      try {
        data = JSON.parse(msg.content.toString());
      } catch (parseErr) {
        console.error("❌ Invalid JSON received. Discarding message.");
        // Reject and do NOT requeue poison-pill messages
        return channel.nack(msg, false, false); 
      }

      console.log("📩 Received payload for API");

      try {
        await axios.post(API, data);
        console.log("✅ Sent to Composite Service");
        
        channel.ack(msg);
      } catch (err) {
        console.error(`❌ API Request Failed: ${err.message}`);
        
        // BEST PRACTICE: Explicitly handle the failure so it doesn't hang in "Unacked" state.
        // requeue: false means it will be dropped (or sent to a Dead Letter Exchange if configured).
        // Change the third parameter to 'true' if you want it to jump back into the queue.
        channel.nack(msg, false, false); 
      }
    });
  } catch (startupErr) {
    console.error("❌ Failed to start consumer:", startupErr.message);
    process.exit(1);
  }
}

// BEST PRACTICE: Graceful shutdown to close connections and finish in-flight tasks
async function shutdown() {
  console.log("\n🛑 Shutting down gracefully...");
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

startConsumer();