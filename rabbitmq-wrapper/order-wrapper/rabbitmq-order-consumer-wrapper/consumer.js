require("dotenv").config();
const amqp = require("amqplib");
const axios = require("axios");

const RABBITMQ_URL = process.env.RABBITMQ_URL;
const QUEUE_NAME = process.env.QUEUE_NAME;
const OUTSYSTEMS_API = process.env.OUTSYSTEMS_API;

const EXCHANGE = "order.exchange";
const ROUTING_KEY = "order.created";

async function startConsumer() {
  try {
    const connection = await amqp.connect(RABBITMQ_URL);
    const channel = await connection.createChannel();

    console.log("Connected to RabbitMQ");

    // 1. Declare exchange
    await channel.assertExchange(EXCHANGE, "topic", { durable: true });

    // 2. Declare queue
    await channel.assertQueue(QUEUE_NAME, { durable: true });

    // 3. Bind queue to exchange
    await channel.bindQueue(QUEUE_NAME, EXCHANGE, ROUTING_KEY);

    console.log(`Bound ${QUEUE_NAME} → ${EXCHANGE} (${ROUTING_KEY})`);

    console.log(`Waiting for messages in ${QUEUE_NAME}...`);

    channel.consume(QUEUE_NAME, async (msg) => {
      if (msg !== null) {
        const content = msg.content.toString();
        console.log("Received:", content);

        try {
          const event = JSON.parse(content);

          await axios.post(OUTSYSTEMS_API, event);

          console.log("Sent to OutSystems");

          channel.ack(msg);

        } catch (err) {
          console.error("Error processing message:", err.message);
          channel.nack(msg, false, false);
        }
      }
    });

  } catch (error) {
    console.error("Failed to start consumer:", error);
  }
}

startConsumer();