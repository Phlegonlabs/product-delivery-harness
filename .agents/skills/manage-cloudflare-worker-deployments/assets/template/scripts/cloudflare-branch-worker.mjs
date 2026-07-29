#!/usr/bin/env node

import { createHash } from "node:crypto";
import { appendFileSync, readFileSync } from "node:fs";
import { resolve } from "node:path";
import { pathToFileURL } from "node:url";
import { spawnSync } from "node:child_process";

const DEFAULT_CONFIG_PATH = ".cloudflare/branch-workers.json";
const NAME_PATTERN = /^[a-z][a-z0-9-]*$/;

function fail(message) {
  throw new Error(message);
}

function requiredString(value, label) {
  if (typeof value !== "string" || value.trim() === "") fail(`${label} must be a non-empty string`);
  return value;
}

function stringArray(value, label) {
  if (!Array.isArray(value) || value.some((item) => typeof item !== "string" || item === "")) {
    fail(`${label} must be an array of non-empty strings`);
  }
  return value;
}

function commandConfig(value, label, { optional = false } = {}) {
  if ((value === null || value === undefined) && optional) return null;
  if (typeof value !== "object" || value === null) fail(`${label} must be an object`);
  if (!Array.isArray(value.command) || value.command.length === 0 || value.command.some((item) => typeof item !== "string")) {
    fail(`${label}.command must be a non-empty string array`);
  }
  return {
    command: value.command,
    cwd: typeof value.cwd === "string" && value.cwd !== "" ? value.cwd : ".",
  };
}

export function validateConfig(value) {
  if (typeof value !== "object" || value === null) fail("configuration must be an object");

  const workerPrefix = requiredString(value.workerPrefix, "workerPrefix");
  if (!NAME_PATTERN.test(workerPrefix) || workerPrefix.endsWith("-")) {
    fail("workerPrefix must start with a lowercase letter and contain only lowercase letters, numbers, and internal dashes");
  }

  const maxWorkerNameLength = value.maxWorkerNameLength ?? 48;
  if (!Number.isInteger(maxWorkerNameLength) || maxWorkerNameLength < 24 || maxWorkerNameLength > 63) {
    fail("maxWorkerNameLength must be an integer between 24 and 63");
  }

  const protectedBranches = stringArray(value.protectedBranches ?? ["main"], "protectedBranches");
  const protectedWorkers = stringArray(value.protectedWorkers ?? [], "protectedWorkers");
  if (protectedWorkers.some((name) => !NAME_PATTERN.test(name))) {
    fail("protectedWorkers contains an invalid Worker name");
  }

  const wranglerValue = value.wrangler;
  if (typeof wranglerValue !== "object" || wranglerValue === null) fail("wrangler must be an object");
  const wranglerCommand = commandConfig(wranglerValue, "wrangler");
  const wranglerEnvironment = requiredString(wranglerValue.environment, "wrangler.environment");
  const wranglerConfig =
    wranglerValue.config === null || wranglerValue.config === undefined
      ? null
      : requiredString(wranglerValue.config, "wrangler.config");

  const deleteForce = value.delete?.force ?? false;
  if (typeof deleteForce !== "boolean") fail("delete.force must be a boolean");

  const productionValue = value.production;
  let production = null;
  if (productionValue !== null && productionValue !== undefined) {
    if (typeof productionValue !== "object") fail("production must be an object or null");
    const workerName = requiredString(productionValue.workerName, "production.workerName");
    if (!NAME_PATTERN.test(workerName)) fail("production.workerName must be a valid Worker name");
    if (!protectedWorkers.includes(workerName)) {
      fail("production.workerName must also be listed in protectedWorkers");
    }
    if (workerName.startsWith(`${workerPrefix}-`)) {
      fail("production.workerName must not use the disposable preview prefix");
    }
    const environment = requiredString(productionValue.environment, "production.environment");
    if (environment === wranglerEnvironment) {
      fail("production.environment must differ from wrangler.environment");
    }
    const config =
      productionValue.config === null || productionValue.config === undefined
        ? wranglerConfig
        : requiredString(productionValue.config, "production.config");
    production = { workerName, environment, config };
  }

  return {
    workerPrefix,
    protectedBranches,
    protectedWorkers,
    maxWorkerNameLength,
    workersDevSubdomain: requiredString(value.workersDevSubdomain, "workersDevSubdomain"),
    install: commandConfig(value.install, "install"),
    verify: commandConfig(value.verify, "verify"),
    build: commandConfig(value.build, "build"),
    wrangler: {
      command: wranglerCommand.command,
      cwd: wranglerCommand.cwd,
      environment: wranglerEnvironment,
      config: wranglerConfig,
    },
    production,
    afterDeploy: commandConfig(value.afterDeploy, "afterDeploy", { optional: true }),
    delete: { force: deleteForce },
  };
}

export function branchName(value) {
  return requiredString(value, "branch").replace(/^refs\/heads\//, "");
}

export function workerNameForBranch(rawBranch, config) {
  const branch = branchName(rawBranch);
  if (config.protectedBranches.includes(branch)) fail(`refusing to operate on protected branch: ${branch}`);

  const hash = createHash("sha256").update(branch).digest("hex").slice(0, 8);
  const baseSlug =
    branch
      .normalize("NFKD")
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "") || "branch";
  const fixedLength = config.workerPrefix.length + hash.length + 2;
  const slugLength = config.maxWorkerNameLength - fixedLength;
  if (slugLength < 1) fail("workerPrefix leaves no room for a branch slug");

  const slug = baseSlug.slice(0, slugLength).replace(/-+$/g, "") || "branch";
  const workerName = `${config.workerPrefix}-${slug}-${hash}`;
  assertPreviewWorker(workerName, config);
  return workerName;
}

export function assertPreviewWorker(workerName, config) {
  if (!workerName.startsWith(`${config.workerPrefix}-`)) {
    fail(`refusing to operate outside prefix ${config.workerPrefix}-`);
  }
  if (config.protectedWorkers.includes(workerName)) fail(`refusing to operate on protected Worker: ${workerName}`);
  if (!NAME_PATTERN.test(workerName) || workerName.length > config.maxWorkerNameLength) {
    fail(`generated Worker name is invalid: ${workerName}`);
  }
}

function loadConfig() {
  const relativePath = process.env.BRANCH_WORKER_CONFIG || DEFAULT_CONFIG_PATH;
  const configPath = resolve(process.cwd(), relativePath);
  return validateConfig(JSON.parse(readFileSync(configPath, "utf8")));
}

function workerUrl(workerName, config) {
  return `https://${workerName}.${config.workersDevSubdomain}.workers.dev`;
}

function workflowOutput(name, value) {
  if (!process.env.GITHUB_OUTPUT) return;
  appendFileSync(process.env.GITHUB_OUTPUT, `${name}=${value}\n`);
}

function requireCloudflareCredentials() {
  return {
    accountId: requiredString(process.env.CLOUDFLARE_ACCOUNT_ID, "CLOUDFLARE_ACCOUNT_ID"),
    apiToken: requiredString(process.env.CLOUDFLARE_API_TOKEN, "CLOUDFLARE_API_TOKEN"),
  };
}

function runConfiguredStep(step, label, extraEnv) {
  const [executable, ...args] = step.command;
  const result = spawnSync(executable, args, {
    cwd: resolve(process.cwd(), step.cwd),
    env: { ...process.env, ...extraEnv },
    stdio: "inherit",
    shell: false,
  });
  if (result.error) fail(`${label} could not start: ${result.error.message}`);
  if (result.status !== 0) fail(`${label} failed with exit code ${result.status ?? "unknown"}`);
}

function previewContext(branch, config) {
  const workerName = workerNameForBranch(branch, config);
  const url = workerUrl(workerName, config);
  return {
    workerName,
    url,
    extraEnv: {
      BRANCH_WORKER_NAME: workerName,
      BRANCH_WORKER_URL: url,
    },
  };
}

function prepareWorker(branch, config) {
  const { extraEnv } = previewContext(branch, config);
  runConfiguredStep(config.install, "install", extraEnv);
  runConfiguredStep(config.verify, "verify", extraEnv);
  runConfiguredStep(config.build, "build", extraEnv);
}

function requireProduction(config) {
  if (!config.production) fail("production deployment is not configured");
  return config.production;
}

function productionContext(config) {
  const production = requireProduction(config);
  return {
    ...production,
    extraEnv: {
      DEPLOYMENT_ENVIRONMENT: "production",
      PRODUCTION_WORKER_NAME: production.workerName,
    },
  };
}

function prepareProduction(config) {
  const { extraEnv } = productionContext(config);
  runConfiguredStep(config.install, "install", extraEnv);
  runConfiguredStep(config.verify, "verify", extraEnv);
  runConfiguredStep(config.build, "build", extraEnv);
}

export function productionDeployArgs(config) {
  const { workerName, environment, config: productionConfig } = productionContext(config);
  const args = [
    "deploy",
    "--cwd",
    config.wrangler.cwd,
    "--env",
    environment,
    "--name",
    workerName,
  ];
  if (productionConfig) args.push("--config", productionConfig);
  return args;
}

function deployProduction(config) {
  requireCloudflareCredentials();
  const { workerName, extraEnv } = productionContext(config);
  const [executable, ...baseArgs] = config.wrangler.command;
  const args = [...baseArgs, ...productionDeployArgs(config)];

  const result = spawnSync(executable, args, {
    cwd: process.cwd(),
    env: { ...process.env, ...extraEnv },
    stdio: "inherit",
    shell: false,
  });
  if (result.error) fail(`Production Wrangler deploy could not start: ${result.error.message}`);
  if (result.status !== 0) {
    fail(`Production Wrangler deploy failed with exit code ${result.status ?? "unknown"}`);
  }

  workflowOutput("worker_name", workerName);
  console.log(`Production Worker: ${workerName}`);
}

function printProductionPlan(config) {
  const { workerName, environment, config: productionConfig } = productionContext(config);
  console.log(
    JSON.stringify(
      {
        workerName,
        wranglerEnvironment: environment,
        wranglerConfig: productionConfig,
        manualDeploymentOnly: true,
      },
      null,
      2,
    ),
  );
}

function deployWorker(branch, config) {
  requireCloudflareCredentials();
  const { workerName, url, extraEnv } = previewContext(branch, config);
  const [executable, ...baseArgs] = config.wrangler.command;
  const args = [
    ...baseArgs,
    "deploy",
    "--cwd",
    config.wrangler.cwd,
    "--env",
    config.wrangler.environment,
    "--name",
    workerName,
  ];
  if (config.wrangler.config) args.push("--config", config.wrangler.config);

  const result = spawnSync(executable, args, {
    cwd: process.cwd(),
    env: { ...process.env, ...extraEnv },
    stdio: "inherit",
    shell: false,
  });
  if (result.error) fail(`Wrangler deploy could not start: ${result.error.message}`);
  if (result.status !== 0) fail(`Wrangler deploy failed with exit code ${result.status ?? "unknown"}`);

  workflowOutput("worker_name", workerName);
  workflowOutput("worker_url", url);
  console.log(`Worker: ${workerName}`);
  console.log(`URL: ${url}`);
}

function afterDeploy(branch, config) {
  const { extraEnv } = previewContext(branch, config);
  if (config.afterDeploy) runConfiguredStep(config.afterDeploy, "afterDeploy", extraEnv);
}

async function cloudflareRequest(path, init, credentials) {
  const response = await fetch(`https://api.cloudflare.com/client/v4${path}`, {
    ...init,
    headers: {
      authorization: `Bearer ${credentials.apiToken}`,
      "content-type": "application/json",
      ...(init?.headers ?? {}),
    },
  });
  const text = await response.text();
  let payload = null;
  if (text) {
    try {
      payload = JSON.parse(text);
    } catch {
      payload = { errors: [{ message: text }] };
    }
  }
  return { response, payload };
}

function cloudflareError(action, response, payload) {
  const messages = Array.isArray(payload?.errors)
    ? payload.errors.map((item) => item?.message).filter(Boolean).join("; ")
    : "";
  return `${action} failed (${response.status})${messages ? `: ${messages}` : ""}`;
}

async function deleteWorker(branch, config) {
  const credentials = requireCloudflareCredentials();
  const workerName = workerNameForBranch(branch, config);
  assertPreviewWorker(workerName, config);
  const scriptPath = `/accounts/${encodeURIComponent(credentials.accountId)}/workers/scripts/${encodeURIComponent(workerName)}`;

  const current = await cloudflareRequest(`${scriptPath}/settings`, { method: "GET" }, credentials);
  if (current.response.status === 404) {
    console.log(`Worker already absent: ${workerName}`);
    return;
  }
  if (!current.response.ok || current.payload?.success === false) {
    fail(cloudflareError("Cloudflare Worker lookup", current.response, current.payload));
  }

  const forceQuery = config.delete.force ? "?force=true" : "";
  const deleted = await cloudflareRequest(`${scriptPath}${forceQuery}`, { method: "DELETE" }, credentials);
  if (deleted.response.status === 404) {
    console.log(`Worker already absent: ${workerName}`);
    return;
  }
  if (!deleted.response.ok || deleted.payload?.success === false) {
    fail(cloudflareError("Cloudflare Worker delete", deleted.response, deleted.payload));
  }
  console.log(`Deleted Worker: ${workerName}`);
}

function printPlan(branch, config) {
  const workerName = workerNameForBranch(branch, config);
  console.log(
    JSON.stringify(
      {
        branch: branchName(branch),
        workerName,
        workerUrl: workerUrl(workerName, config),
        deleteForce: config.delete.force,
      },
      null,
      2,
    ),
  );
}

async function main(argv = process.argv.slice(2)) {
  const [command, branch] = argv;
  const branchCommands = ["name", "url", "plan", "prepare", "deploy", "after-deploy", "delete"];
  const productionCommands = ["production-plan", "production-prepare", "production-deploy"];
  if (!branchCommands.includes(command) && !productionCommands.includes(command)) {
    fail(
      "usage: cloudflare-branch-worker.mjs <name|url|plan|prepare|deploy|after-deploy|delete> <branch> | <production-plan|production-prepare|production-deploy>",
    );
  }
  if (branchCommands.includes(command) && !branch) {
    fail(`branch is required for ${command}`);
  }

  const config = loadConfig();
  if (command === "name") console.log(workerNameForBranch(branch, config));
  if (command === "url") console.log(workerUrl(workerNameForBranch(branch, config), config));
  if (command === "plan") printPlan(branch, config);
  if (command === "prepare") prepareWorker(branch, config);
  if (command === "deploy") deployWorker(branch, config);
  if (command === "after-deploy") afterDeploy(branch, config);
  if (command === "delete") await deleteWorker(branch, config);
  if (command === "production-plan") printProductionPlan(config);
  if (command === "production-prepare") prepareProduction(config);
  if (command === "production-deploy") deployProduction(config);
}

const invokedPath = process.argv[1] ? pathToFileURL(resolve(process.argv[1])).href : "";
if (import.meta.url === invokedPath) {
  main().catch((error) => {
    console.error(error instanceof Error ? error.message : error);
    process.exitCode = 1;
  });
}
