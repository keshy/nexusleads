FROM node:20-alpine

# CA certificates are included in Alpine by default (needed by Codex CLI's Rust HTTP client)
RUN apk add --no-cache ca-certificates

WORKDIR /app

# Copy package files
COPY package.json package-lock.json* ./

# Install dependencies
RUN npm install --production

# Install Codex CLI globally (required by SDK for sandboxed execution)
RUN npm install -g @openai/codex

# Copy application code
COPY . .

# Use built-in non-root node user
RUN chown -R node:node /app
USER node

EXPOSE 3001

CMD ["node", "server.js"]
