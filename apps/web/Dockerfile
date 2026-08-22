FROM oven/bun:1.3.14 AS builder

WORKDIR /repo

COPY package.json bun.lock turbo.json ./
COPY apps/web/package.json apps/web/package.json
COPY apps/api/package.json apps/api/package.json

RUN bun install --frozen-lockfile

RUN L=$(ls -d /repo/node_modules/.bun/nitro-nightly@*/node_modules) && ln -s nitro-nightly "$L/nitro"

COPY apps/web apps/web

RUN cd apps/web && bun run build

FROM oven/bun:1.3.14

WORKDIR /srv

COPY --from=builder /repo/apps/web/.output ./.output

USER bun
ENV PORT=3000 NODE_ENV=production

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD bun -e "const r=await fetch('http://localhost:3000');if(!r.ok)process.exit(1)"

CMD ["bun", ".output/server/index.mjs"]
