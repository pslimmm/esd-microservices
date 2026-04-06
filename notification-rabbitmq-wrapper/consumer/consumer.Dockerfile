# Use a slim version of Node for a smaller image size
FROM node:20-alpine

# Create app directory
WORKDIR /usr/src/app

# Install dependencies first (better caching)
COPY package*.json ./
RUN npm i --production

# Copy the rest of your code
COPY . .

# Run the consumer
CMD [ "node", "consumer.js" ]