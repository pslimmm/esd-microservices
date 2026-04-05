we are using arrival-alert-wrapper only,
order-wrapper is no longer used as we decided to directly use http

setup:

add .env in 
- rabbitmq-wrapper\arrival-alert-wrapper\rabbitmq-arrival-consumer-wrapper
- rabbitmq-wrapper\arrival-alert-wrapper\rabbitmq-arrival-publisher-wrapper

still in the main rabbitmq-wrapper:
  docker compose up -d

then:
cd 'rabbitmq-wrapper\arrival-alert-wrapper\rabbitmq-arrival-publisher-wrapper'
node index

cd 'rabbitmq-wrapper\arrival-alert-wrapper\rabbitmq-arrival-consumer-wrapper'
node consumer