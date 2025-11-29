#!/usr/bin/env node
import yargs from "yargs";
import { hideBin } from "yargs/helpers";
import {
  getCommandRunner
} from "./commandRunner";
import { loadConfig } from "./config";
import { ChokidarFileWatcher } from "./fileWatcher";
import { startWatcher, WatcherDependencies } from "./watcher";

async function main(): Promise<void> {
  const argv = yargs(hideBin(process.argv))
    .option("config", {
      type: "string",
      demandOption: true,
      describe: "Path to watcher config JSON file",
    })
    .option("dry-run", {
      type: "boolean",
      default: false,
      describe: "Show commands that would be executed without running them",
    })
    .help()
    .alias("help", "h")
    .parseSync();

  const config = loadConfig(argv.config);

  const fileWatcher = new ChokidarFileWatcher(config.workspacePath, {
    persistent: true,
    ignoreInitial: true,
    ignored: config.ignoreGlobs,
  });

  const dependencies: WatcherDependencies = {
    fileWatcher,
    commandRunner: getCommandRunner(argv["dry-run"], config),
  };

  if (argv["dry-run"]) {
    console.log(
      `[${new Date().toISOString()}] DRY-RUN MODE: Commands will be logged but not executed`
    );
  }

  console.log(`[${new Date().toISOString()}] Watching ${config.workspacePath}`);
  const watcher = startWatcher(config, dependencies);

  const shutdown = async (signal: NodeJS.Signals) => {
    console.log(
      `[${new Date().toISOString()}] Received ${signal}, shutting down watcher`
    );
    await watcher.close();
    process.exit(0);
  };

  process.on("SIGINT", shutdown);
  process.on("SIGTERM", shutdown);
}

main().catch((error) => {
  console.error(error instanceof Error ? error.message : error);
  process.exit(1);
});
