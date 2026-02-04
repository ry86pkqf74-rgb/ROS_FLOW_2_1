import { Client } from "pg";

async function main() {
  const databaseUrl =
    process.env.DATABASE_URL || "postgresql://ros:ros@localhost:5432/ros";

  const client = new Client({ connectionString: databaseUrl });
  await client.connect();

  // Deterministic E2E user (no password)
  const userId = "e2e-test-user-00000000-0000-0000-0000-000000000001";
  const email = "e2e-test@researchflow.local";

  await client.query(
    `
    INSERT INTO users (id, email, first_name, last_name, created_at, updated_at)
    VALUES ($1, $2, $3, $4, NOW(), NOW())
    ON CONFLICT (id) DO NOTHING
    `,
    [userId, email, "E2E", "TestUser"]
  );

  await client.end();

  console.log(`[seed] Seeded user id=${userId} email=${email}`);
}

main().catch((err) => {
  console.error("[seed] Failed:", err);
  process.exit(1);
});
