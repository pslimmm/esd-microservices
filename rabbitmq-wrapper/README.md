we are using arrival-alert-wrapper only,
order-wrapper is no longer used as we decided to directly use http

setup:
add .env in using .env.example
- rabbitmq-wrapper\arrival-alert-wrapper\

still in the main rabbitmq-wrapper folder:
```
docker compose up -d
```
then:
```
cd 'rabbitmq-wrapper\arrival-alert-wrapper
npm i or pnpm i
node index
```

and in another terminal window:
```
node consumer
```