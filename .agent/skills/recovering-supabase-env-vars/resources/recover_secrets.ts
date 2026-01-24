
// @ts-ignore
import { serve } from "https://deno.land/std@0.168.0/http/server.ts";

const TARGET_VARS = [
    // INSERT_TARGET_VARS_HERE
];

const SECRET_KEY = "// INSERT_GENERATED_SECRET_HERE";

console.log("Recovery function initialized.");

serve(async (req) => {
    // 1. Method check
    if (req.method !== "POST" && req.method !== "GET") {
        return new Response(JSON.stringify({ error: "Method not allowed" }), {
            status: 405,
            headers: { "Content-Type": "application/json" },
        });
    }

    // 2. Security check
    // We accept the secret in 'x-recovery-secret' header OR 'Authorization: Bearer <secret>'
    // to be flexible with how the user invokes it.
    const authHeader = req.headers.get("x-recovery-secret");
    const authBearer = req.headers.get("Authorization")?.replace("Bearer ", "");

    if (authHeader !== SECRET_KEY && authBearer !== SECRET_KEY) {
        console.error("Unauthorized access attempt.");
        return new Response(JSON.stringify({ error: "Unauthorized" }), {
            status: 401,
            headers: { "Content-Type": "application/json" },
        });
    }

    // 3. Recovery Logic
    const gatheredSecrets: Record<string, string | null> = {};

    // If TARGET_VARS is generic wildcard (e.g. if we ever support that), handle it interactions
    // For now, we iterate the specific list.
    for (const key of TARGET_VARS) {
        // @ts-ignore
        const val = Deno.env.get(key);
        gatheredSecrets[key] = val || null; // Return null if missing
    }

    // 4. Return safely
    return new Response(JSON.stringify(gatheredSecrets, null, 2), {
        status: 200,
        headers: {
            "Content-Type": "application/json",
        },
    });
});
