FROM node:20-alpine

WORKDIR /app

COPY package.json ./
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm install --legacy-peer-deps

COPY . .

ENV NEXT_IGNORE_INCORRECT_LOCKFILE=1
RUN npm run build

EXPOSE 3000

CMD ["npm", "run", "start"]
