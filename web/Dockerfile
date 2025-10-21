# web/Dockerfile
FROM node:20-alpine

WORKDIR /app

# Build-time version (from CI) → exposed to the client
ARG VERSION="0.0.0-dev"
ENV NEXT_PUBLIC_APP_VERSION=${VERSION}

# Workaround: force Next.js to use SWC WASM in Alpine to avoid native parser issues
ENV NEXT_DISABLE_SWC_NATIVE=true

# If you have a base URL for the API at build time, you can also set:
# ENV NEXT_PUBLIC_API_BASE=/api

# Install deps (use package-lock.json if you have it)
COPY package*.json ./
RUN npm ci

# Copy source and build
COPY . .
RUN npm run build

EXPOSE 3000

# Simple healthcheck for the container
HEALTHCHECK --interval=20s --timeout=5s --start-period=10s --retries=5 \
  CMD ["sh", "-c", "wget -qO- http://127.0.0.1:3000 >/dev/null || exit 1"]

# Start Next.js (production)
CMD ["npm", "run", "start"]
