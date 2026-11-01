FROM node:22-alpine AS build
RUN corepack enable
WORKDIR /app
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY apps/web/package.json ./apps/web/package.json
COPY packages/api-client/package.json ./packages/api-client/package.json
RUN pnpm install --frozen-lockfile
COPY apps/web ./apps/web
COPY packages/api-client ./packages/api-client
ENV PLACEMENTOS_STANDALONE=true
RUN pnpm --filter @placementos/api-client build && pnpm --filter @placementos/web build

FROM node:22-alpine AS runtime
ENV NODE_ENV=production HOSTNAME=0.0.0.0 PORT=3000
RUN addgroup -S placementos && adduser -S placementos -G placementos
WORKDIR /app
COPY --from=build --chown=placementos:placementos /app/apps/web/.next/standalone ./
COPY --from=build --chown=placementos:placementos /app/apps/web/.next/static ./apps/web/.next/static
USER placementos
EXPOSE 3000
CMD ["node", "apps/web/server.js"]
