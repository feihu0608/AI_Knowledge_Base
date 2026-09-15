FROM node:24-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
ARG NPM_CONFIG_REGISTRY=https://registry.npmmirror.com
RUN npm ci --no-audit --no-fund --registry "$NPM_CONFIG_REGISTRY" --fetch-retries 5 --fetch-timeout 180000
COPY . .
RUN npm run build
FROM nginx:1.28-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
