require("dotenv").config();
const amqp = require("amqplib");
const axios = require("axios");

const RABBITMQ_URL = process.env.RABBITMQ_URL;
const EXCHANGE = "topic.exchange";
const QUEUE = "notification-queue";

const ROUTING_KEYS = ["order.completed", "order.no_show"];

const NOTIFICATION_API = process.env.NOTIFICATION_API;

//Start consumer
async function startConsumer() {
  try {
    const connection = await amqp.connect(RABBITMQ_URL);
    const channel = await connection.createChannel();

    await channel.assertExchange(EXCHANGE, "topic", { durable: true });
    await channel.assertQueue(QUEUE, { durable: true });

    // Bind BOTH routing keys
    for (const key of ROUTING_KEYS) {
      await channel.bindQueue(QUEUE, EXCHANGE, key);
    }

    console.log("Notification Consumer waiting for messages...");

    channel.consume(QUEUE, async (msg) => {
    if (!msg) return;

    const data = JSON.parse(msg.content.toString());

    console.log("Received:", data);

    try {
      //Transform payload for Notification API
      const payload = {
      email: data.email,
      subject: data.subject || `Order ${data.OrderId} Update`,
      message: data.message || `Your order is now ${data.NewStatus}`,
      notification_type: data.notification_type || "email"
      };

      console.log("Sending to Notification API:", payload);

      await axios.post(NOTIFICATION_API, payload);

      console.log("Notification sent successfully");

      channel.ack(msg);

    } catch (err) {
      console.error("Notification failed:", err.response?.data || err.message);
    }
  });

  } catch (err) {
    console.error("Consumer error:", err);
  }
}

startConsumer();