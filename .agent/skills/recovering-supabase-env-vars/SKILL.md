---
name: recovering-supabase-env-vars
description: Safely recovers write-only environment variables from Supabase by deploying a temporary edge function. Use when the user needs to recover lost secrets from a Supabase project.
---

# Recovering Supabase Environment Variables

## When to use this skill
- User needs to see values of "write-only" environment variables in Supabase.
- User has lost local copies of secrets and needs to recover them from the running project.
- User asks to "audit" or "check" the current environment variables in Supabase.

## Workflow
1.  **Context Gathering**:
    - Ask the user for the list of environment variable names (keys) they need to recover. (e.g., `SMTP_PASSWORD`, `STRIPE_SECRET_KEY`).
    - Ask for the path to their local Supabase project (to run `supabase functions deploy`).
    - Check if they are logged in to Supabase CLI (`supabase projects list`).

2.  **Preparation**:
    - Generate a random High-Entropy Secret Key (e.g., a UUID or long random string) to secure the function.
    - Read the template from `resources/recover_secrets.ts`.
    - Replace `// INSERT_TARGET_VARS_HERE` with the JSON-formatted list of keys the user requested.
    - Replace `// INSERT_GENERATED_SECRET_HERE` with the generated secret key.
    - Save this file to a temporary location in the user's project, e.g., `./supabase/functions/temp_recovery_func/index.ts`.

3.  **Deployment**:
    - Run `supabase functions deploy temp_recovery_func --no-verify-jwt`.
    - Ensure the function is deployed successfully.

4.  **Execution (Recovery)**:
    - Invoke the function using `curl` or a script, passing the secret key in the `x-recovery-secret` header.
    - Example: `curl -H "x-recovery-secret: [GENERATED_SECRET]" https://[PROJECT_REF].supabase.co/functions/v1/temp_recovery_func`
    - **CRITICAL**: Do not print the output to the terminal history if possible, or advise the user to clear it. However, since the goal is recovery, displaying it in the response (markdown block) is usually what the user wants.

5.  **Cleanup**:
    - **IMMEDIATELY** run `supabase functions delete temp_recovery_func` to remove the exposed endpoint.
    - Delete the local file `./supabase/functions/temp_recovery_func/index.ts`.
    - Remove the parent folder `./supabase/functions/temp_recovery_func` if empty.

## Instructions
- **Safety First**: Verify that the user definitely wants to deploy a live endpoint.
- **Minimization**: Only fetch the variables explicitly requested.
- **Ephemeral**: The function must exist for the shortest time possible.
- **No Logs**: The Deno function logic explicitly avoids `console.log(secrets)`. Ensure your AI-generated code continues to respect this.

## Resources
- [Deno Function Template](resources/recover_secrets.ts)
