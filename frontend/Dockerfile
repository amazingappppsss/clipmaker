# ClipMaker web image (Next.js standalone). Build context: repository root.
FROM node:22-slim AS build
WORKDIR /repo
COPY package.json package-lock.json ./
COPY frontend/package.json frontend/
RUN npm ci --workspace frontend --include-workspace-root
COPY common ./common
COPY frontend ./frontend
ARG NEXT_PUBLIC_API_URL
ARG NEXT_PUBLIC_SUPABASE_URL
ARG NEXT_PUBLIC_SUPABASE_ANON_KEY
ARG NEXT_PUBLIC_DEV_AUTH=false
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm --workspace frontend run build

FROM node:22-slim
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1 PORT=3000 HOSTNAME=0.0.0.0
WORKDIR /app
COPY --from=build --chown=node /repo/frontend/.next/standalone ./
COPY --from=build --chown=node /repo/frontend/.next/static ./frontend/.next/static
COPY --from=build --chown=node /repo/frontend/public ./frontend/public
USER node
EXPOSE 3000
HEALTHCHECK --interval=30s --timeout=5s CMD node -e "fetch('http://localhost:3000').then(r=>process.exit(r.ok?0:1)).catch(()=>process.exit(1))"
CMD ["node", "frontend/server.js"]
