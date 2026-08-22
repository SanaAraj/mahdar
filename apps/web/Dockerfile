FROM oven/bun:1.3.14 AS builder

WORKDIR /repo

COPY package.json bun.lock turbo.json ./
COPY apps/web apps/web
COPY apps/api/package.json apps/api/package.json

RUN bun install --frozen-lockfile

RUN cd apps/web && bun run build

FROM oven/bun:1.3.14

WORKDIR /srv

COPY --from=builder /repo/apps/web/.output ./.output

USER bun
ENV PORT=3000 NODE_ENV=production

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD bun -e "const r=await fetch('http://localhost:3000');process.exit(r.ok?0:1)"

CMD ["bun", ".output/server/index.mjs"]
