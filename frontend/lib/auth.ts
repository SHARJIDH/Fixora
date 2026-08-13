/**
 * Better Auth - Server Configuration
 * Using Better Auth's built-in PostgreSQL adapter (Kysely-based)
 * No external ORM required - Better Auth handles schema and migrations
 */
import { betterAuth } from "better-auth";
import { Pool } from "pg";
import { DodoPayments } from "dodopayments";
import { dodopayments, checkout, portal, webhooks } from "@dodopayments/better-auth";

// Debug logging
const databaseUrl = process.env.DATABASE_URL;
const webhookSecret = process.env.DODO_PAYMENTS_WEBHOOK_SECRET || "dummy_webhook_key";
console.log("[Auth Debug] Initializing Better Auth...");
console.log("[Auth Debug] Webhook secret configured:", webhookSecret ? `${webhookSecret.substring(0, 10)}...` : "NOT SET");
console.log("[Auth Debug] Webhook secret length:", webhookSecret?.length);

const dodoClient = new DodoPayments({
  bearerToken: process.env.DODO_PAYMENTS_API_KEY || "dummy_key",
  environment: "test_mode",
});

const pool = new Pool({
  connectionString: databaseUrl,
});

export const auth = betterAuth({
  // Use built-in PostgreSQL adapter - pass Pool directly
  // Better Auth will create tables automatically if they don't exist
  database: pool,
  
  // Base URL for callbacks
  baseURL: process.env.NEXT_PUBLIC_APP_URL || "http://localhost:3000",
  
  // Trusted origins for CORS
  trustedOrigins: [
    "http://localhost:3000",
    process.env.NEXT_PUBLIC_APP_URL || "",
  ].filter(Boolean),
  
  // Email/password auth disabled (only using GitHub)
  emailAndPassword: {
    enabled: false,
  },
  
  // GitHub OAuth
  socialProviders: {
    github: {
      clientId: process.env.GITHUB_CLIENT_ID!,
      clientSecret: process.env.GITHUB_CLIENT_SECRET!,
      // Request repo scope to access user's repositories
      scope: ["read:user", "user:email", "repo"],
    },
  },
  
  user: {
    additionalFields: {
      dodoCustomerId: {
        type: "string",
        required: false,
      },
    }
  },
  
  // Session configuration
  session: {
    expiresIn: 60 * 60 * 24 * 7, // 7 days
    updateAge: 60 * 60 * 24, // 1 day
  },

  plugins: [
    dodopayments({
      client: dodoClient,
      createCustomerOnSignUp: true,
      use: [
        checkout({
          products: [
            { slug: "pro", productId: process.env.DODO_PRO_PRODUCT_ID || "pdt_pro_placeholder" },
            { slug: "ultra", productId: process.env.DODO_ULTRA_PRODUCT_ID || "pdt_ultra_placeholder" },
          ],
        }),
        portal(),
        webhooks({
          webhookKey: webhookSecret,
          onPayload: async (payload: any) => {
            console.log("[Dodo Webhook] Received Event:", payload.type);
          },
          onSubscriptionActive: async (payload: any) => {
            const sub = payload.data;
            const subscriptionId = sub.subscription_id || sub.id;
            const customerId = sub.customer_id || (typeof sub.customer === 'string' ? sub.customer : sub.customer?.id);
            const customerEmail = sub.customer_email || sub.customer?.email;
            
            console.log(`[Dodo Webhook] Processing Activation: ${subscriptionId} (Customer: ${customerId})`);
            
            // Map product ID back to slug
            let plan = "pro";
            if (sub.product_id === process.env.DODO_ULTRA_PRODUCT_ID) {
              plan = "ultra";
            }
            console.log(`[Dodo Webhook] Plan detected: ${plan} for product: ${sub.product_id}`);

            // Find user by customer ID or email
            console.log(`[Dodo Webhook] Searching for user: ${customerEmail} or ${customerId}`);
            const userRes = await pool.query(
              'SELECT id FROM "user" WHERE "dodoCustomerId" = $1 OR email = $2 LIMIT 1',
              [customerId, customerEmail]
            );

            if (userRes.rows.length > 0) {
              const userId = userRes.rows[0].id;
              console.log(`[Dodo Webhook] Found user: ${userId}. Syncing subscription...`);
              
              // Upsert subscription
              await pool.query(
                `INSERT INTO subscription (id, user_id, plan, status, quantity, next_billing_date, updated_at)
                 VALUES ($1, $2, $3, $4, $5, $6, NOW())
                 ON CONFLICT (id) DO UPDATE SET
                   status = $4,
                   plan = $3,
                   quantity = $5,
                   next_billing_date = $6,
                   updated_at = NOW()`,
                [subscriptionId, userId, plan, "active", sub.quantity || 1, sub.next_billing_date]
              );
              
              console.log(`[Dodo Webhook] Successfully synced ${plan} plan for user ${userId}`);

              // Also update User record if dodoCustomerId was missing
              await pool.query(
                'UPDATE "user" SET "dodoCustomerId" = $1 WHERE id = $2 AND "dodoCustomerId" IS NULL',
                [customerId, userId]
              );
            } else {
              console.error(`[Dodo Webhook] CRITICAL: User not found in local DB for customer ${customerId} (${customerEmail})`);
            }
          },
          onSubscriptionCancelled: async (payload: any) => {
            const sub = payload.data;
            const subscriptionId = sub.subscription_id || sub.id;
            console.log(`[Dodo Webhook] Processing Cancellation: ${subscriptionId}`);
            
            const result = await pool.query(
              'UPDATE subscription SET status = $1, updated_at = NOW() WHERE id = $2',
              ["cancelled", subscriptionId]
            );
            
            if (result.rowCount && result.rowCount > 0) {
              console.log(`[Dodo Webhook] Cancelled subscription ${subscriptionId} in local DB`);
            } else {
              console.warn(`[Dodo Webhook] Subscription ${subscriptionId} not found in local DB for cancellation`);
            }
          }
        }),
      ],
    }),
  ],
  
  // Backfill Dodo Customer ID for existing users who sign in
  events: {
    signIn: {
      succeeded: async ({ user }: { user: any }) => {
        if (!user.dodoCustomerId) {
          console.log(`[Auth] User ${user.email} missing Dodo ID. Creating now...`);
          try {
            const customer = await dodoClient.customers.create({
              email: user.email,
              name: user.name,
            });
            
            // Dodo SDK uses customer_id
            const dodoId = (customer as any).customer_id || (customer as any).id;
            
            if (dodoId) {
              await pool.query(
                'UPDATE "user" SET "dodoCustomerId" = $1 WHERE id = $2',
                [dodoId, user.id]
              );
              console.log(`[Auth] Created Dodo ID for existing user: ${dodoId}`);
            }
          } catch (err) {
            console.error("[Auth] Failed to backfill Dodo ID:", err);
          }
        }
      },
    },
  },
  
  // Debug logging for development
  logger: {
    disabled: false,
    level: "debug",
  },
});

export type Session = typeof auth.$Infer.Session;
