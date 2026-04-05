require("dotenv").config();
const amqp = require("amqplib");
const axios = require("axios");

const RABBITMQ_URL = process.env.RABBITMQ_URL;
const EXCHANGE = "topic.exchange";
const QUEUE = "gantry-queue";

//Only listen to completed orders
const ROUTING_KEY = "order.completed";

const GANTRY_API = process.env.GANTRY_API;

async function startConsumer() {
  try {
    const connection = await amqp.connect(RABBITMQ_URL);
    const channel = await connection.createChannel();

    await channel.assertExchange(EXCHANGE, "topic", { durable: true });
    await channel.assertQueue(QUEUE, { durable: true });

    //Bind Only order.completed
    await channel.bindQueue(QUEUE, EXCHANGE, ROUTING_KEY);

    console.log("🚧 Gantry Consumer waiting for messages...");

    channel.consume(QUEUE, async (msg) => {
    if (!msg) return;

    const data = JSON.parse(msg.content.toString());

    console.log("Received (Gantry):", data);

    try {
        //MUST HAVE Plate_Num
        const plateNum = data.Plate_Num;

        if (!plateNum) {
        throw new Error("Missing Plate_Num in message");
        }

        //Transform payload
        const payload = {
        OrderId: data.OrderId,
        NewStatus: data.NewStatus,
        UpdatedBy: data.UpdatedBy
        };

        const url = `${GANTRY_API}/plate/${plateNum}`;

        console.log("➡️ Calling Gantry API:", url);
        console.log("➡️ Payload:", payload);

        await axios.put(url, payload);

        console.log("Gantry updated successfully");

        channel.ack(msg);

    } catch (err) {
        console.error("Gantry API failed:", err.response?.data || err.message);
    }
    });

  } catch (err) {
    console.error("Gantry consumer error:", err);
  }
}

startConsumer();