import type { ReactNode } from "react";
import { HeadContent, Scripts, Outlet, createRootRouteWithContext } from "@tanstack/react-router";
import { TanStackRouterDevtoolsPanel } from "@tanstack/react-router-devtools";
import { TanStackDevtools } from "@tanstack/react-devtools";
import { QueryClientProvider, type QueryClient } from "@tanstack/react-query";
import { DirectionProvider } from "@radix-ui/react-direction";

import appCss from "../styles/app.css?url";
import { queryClient } from "../lib/query-client";
import { IconSprite } from "../components/icon-sprite";

interface RouterContext {
  queryClient: QueryClient;
}

export const Route = createRootRouteWithContext<RouterContext>()({
  head: () => ({
    meta: [
      { charSet: "utf-8" },
      { name: "viewport", content: "width=device-width, initial-scale=1" },
      { title: "محضر | تفريغ الاجتماعات" },
      { name: "description", content: "تسجيل الاجتماعات وتفريغها الصوتي بالعربية" },
    ],
    links: [{ rel: "stylesheet", href: appCss }],
  }),
  shellComponent: RootDocument,
});

function RootDocument({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html dir="rtl" lang="ar">
      <head>
        <HeadContent />
      </head>
      <body>
        <DirectionProvider dir="rtl">
          <QueryClientProvider client={queryClient}>
            <IconSprite />
            {children ?? <Outlet />}
            <TanStackDevtools
              config={{ position: "bottom-right" }}
              plugins={[{ name: "Tanstack Router", render: <TanStackRouterDevtoolsPanel /> }]}
            />
          </QueryClientProvider>
        </DirectionProvider>
        <Scripts />
      </body>
    </html>
  );
}
