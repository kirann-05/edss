# The EDSS web app. Built from the frontend folder: docker build frontend
# The API's address is read at build time, because Next.js bakes its rewrites into the build.
FROM node:22-slim AS build
ARG EDSS_API_ORIGIN=http://backend:8000
ENV EDSS_API_ORIGIN=$EDSS_API_ORIGIN EDSS_STANDALONE=1 NEXT_TELEMETRY_DISABLED=1
WORKDIR /web
RUN corepack enable
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile
COPY . .
# public/ may be empty, and git keeps no empty folder, so a fresh clone has none
RUN mkdir -p public && pnpm build

FROM node:22-slim
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1 HOSTNAME=0.0.0.0 PORT=3000
WORKDIR /web
COPY --from=build --chown=node /web/.next/standalone ./
COPY --from=build --chown=node /web/.next/static ./.next/static
COPY --from=build --chown=node /web/public ./public
USER node
EXPOSE 3000
HEALTHCHECK --interval=5s --timeout=3s --start-period=15s --retries=10 \
  CMD node -e "fetch('http://127.0.0.1:3000/login').then(r => process.exit(r.ok ? 0 : 1)).catch(() => process.exit(1))"
CMD ["node", "server.js"]
