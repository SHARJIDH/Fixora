import { createAuthClient } from "better-auth/react";
import { dodopaymentsClient } from "@dodopayments/better-auth";
import { inferAdditionalFields } from "better-auth/client/plugins";

export const authClient = createAuthClient({
  baseURL: process.env.NEXT_PUBLIC_APP_URL || "http://localhost:3000",
  plugins: [
    dodopaymentsClient(),
    inferAdditionalFields({
      user: {
        dodoCustomerId: {
          type: "string",
          required: false,
        },
      },
    }),
  ],
});

// Export convenience hooks
export const { signIn, signOut, useSession } = authClient;
