import React from "react";
import ReactDOM from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { RouterProvider } from "react-router-dom";

import { AuthProvider } from "./auth/auth.store";
import { TimeProvider } from "./context/TimeContext";
import { router } from "./router";

import "./index.css";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: false,
    },
  },
});

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <TimeProvider>
          <RouterProvider router={router} />
        </TimeProvider>
      </AuthProvider>
    </QueryClientProvider>
  </React.StrictMode>
);
