FROM node:18-alpine AS builder

WORKDIR /app

COPY package.json package-lock.json ./

RUN npm install

COPY . .

RUN npm run build

FROM node:18-alpine AS runner

WORKDIR /app

COPY --from=builder /app/next.config.mjs ./
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package.json ./package.json
COPY --from=builder /app/server.js ./server.js

EXPOSE 3000

ENV NODE_ENV production

# If no url is set we assume that it's local
ENV OWL_API_URL=http://host.docker.internal:8000

# Start the app with the custom server if it's local for proxying, otherwise start the normal server
CMD ["/bin/sh", "-c", "if [ \"$OWL_API_URL\" = 'http://host.docker.internal:8000' ]; then npm run startCustom; else npm start; fi"]

