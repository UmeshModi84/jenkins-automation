FROM node:20-alpine   

WORKDIR /app

ENV NODE_ENV=production
ENV PORT=3000

COPY backend/package.json backend/package-lock.json ./
RUN npm ci --omit=dev

COPY backend/ ./

RUN mkdir -p /app/var/ai-reports && chown -R node:node /app/var

EXPOSE 3000

USER node

CMD ["node", "src/index.js"]
