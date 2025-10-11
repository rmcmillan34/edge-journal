# web/Dockerfile
FROM node:20-alpine
WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm install

ARG VERSION="0.0.0-dev"
ENV NEXT_PUBLIC_APP_VERSION="${VERSION}"
RUN printf "%s" "${NEXT_PUBLIC_APP_VERSION}" > /app/VERSION

# Build-time env for Next.js
ARG VERSION
ENV NEXT_PUBLIC_APP_VERSION=${VERSION}

COPY . .
EXPOSE 3000
CMD ["npm", "run", "dev"]
