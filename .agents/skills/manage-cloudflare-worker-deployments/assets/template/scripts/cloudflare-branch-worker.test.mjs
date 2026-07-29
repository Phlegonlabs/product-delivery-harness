import assert from "node:assert/strict";
import test from "node:test";
import {
  assertPreviewWorker,
  productionDeployArgs,
  validateConfig,
  workerNameForBranch,
} from "./cloudflare-branch-worker.mjs";

function config(overrides = {}) {
  return validateConfig({
    workerPrefix: "example-preview",
    protectedBranches: ["main"],
    protectedWorkers: ["example", "example-production"],
    maxWorkerNameLength: 48,
    workersDevSubdomain: "example-account",
    install: { command: ["npm", "ci"], cwd: "." },
    verify: { command: ["npm", "test"], cwd: "." },
    build: { command: ["npm", "run", "build"], cwd: "." },
    wrangler: {
      command: ["npx", "wrangler"],
      cwd: ".",
      environment: "development",
      config: null,
    },
    afterDeploy: null,
    delete: { force: false },
    ...overrides,
  });
}

test("creates a stable, safe Worker name", () => {
  const selected = config();
  const first = workerNameForBranch("feature/Better Search", selected);
  const second = workerNameForBranch("feature/Better Search", selected);

  assert.equal(first, second);
  assert.match(first, /^example-preview-feature-better-search-[a-f0-9]{8}$/);
  assert.ok(first.length <= selected.maxWorkerNameLength);
});

test("adds a hash so similar slugs do not collide", () => {
  const selected = config();
  assert.notEqual(
    workerNameForBranch("feature/a_b", selected),
    workerNameForBranch("feature/a-b", selected),
  );
});

test("refuses a protected branch", () => {
  assert.throws(() => workerNameForBranch("main", config()), /protected branch/);
});

test("refuses a Worker outside the configured prefix", () => {
  assert.throws(() => assertPreviewWorker("production-worker", config()), /outside prefix/);
});

test("caps long branch names", () => {
  const selected = config({ maxWorkerNameLength: 32 });
  const workerName = workerNameForBranch(`feature/${"long-".repeat(30)}`, selected);
  assert.equal(workerName.length, 32);
});

test("accepts production only when its Worker is protected and outside the preview prefix", () => {
  const selected = config({
    production: {
      workerName: "example-production",
      environment: "production",
      config: null,
    },
  });
  assert.equal(selected.production.workerName, "example-production");
  assert.equal(selected.production.environment, "production");
});

test("refuses an unprotected production Worker", () => {
  assert.throws(
    () =>
      config({
        production: {
          workerName: "other-production",
          environment: "production",
          config: null,
        },
      }),
    /listed in protectedWorkers/,
  );
});

test("refuses to reuse the preview environment for production", () => {
  assert.throws(
    () =>
      config({
        production: {
          workerName: "example-production",
          environment: "development",
          config: null,
        },
      }),
    /must differ/,
  );
});

test("builds an explicit production Wrangler deployment command", () => {
  const selected = config({
    production: {
      workerName: "example-production",
      environment: "production",
      config: "wrangler.jsonc",
    },
  });
  assert.deepEqual(productionDeployArgs(selected), [
    "deploy",
    "--cwd",
    ".",
    "--env",
    "production",
    "--name",
    "example-production",
    "--config",
    "wrangler.jsonc",
  ]);
});
