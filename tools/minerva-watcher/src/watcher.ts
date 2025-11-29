import path from 'path';
import { FileWatcher } from './fileWatcher';
import { CommandRunner } from './commandRunner';
import { ResolvedWatcherConfig } from './types';

export interface WatcherDependencies {
  fileWatcher: FileWatcher;
  commandRunner: CommandRunner;
}

export function startWatcher(
  config: ResolvedWatcherConfig,
  dependencies: WatcherDependencies,
): FileWatcher {
  const pendingFiles = new Set<string>();
  let debounceTimer: NodeJS.Timeout | null = null;
  let runInProgress = false;
  let needsRun = false;
  let awaitingChangeAfterFailure = false;

  const enqueueChange = (filePath: string) => {
    const normalized = path.resolve(filePath);
    if (!shouldTrack(normalized, config)) {
      return;
    }
    pendingFiles.add(normalized);
    if (config.logChangedFiles) {
      console.log(`[${new Date().toISOString()}] change detected: ${relativeToWorkspace(normalized, config.workspacePath)}`);
    }
    if (awaitingChangeAfterFailure) {
      awaitingChangeAfterFailure = false;
    }
    scheduleDebouncedRun();
  };

  function scheduleDebouncedRun() {
    if (debounceTimer) {
      clearTimeout(debounceTimer);
    }
    debounceTimer = setTimeout(() => {
      debounceTimer = null;
      if (pendingFiles.size === 0) {
        return;
      }
      needsRun = true;
      triggerRun();
    }, config.debounceMs);
  }

  async function triggerRun() {
    if (runInProgress || awaitingChangeAfterFailure) {
      return;
    }
    runInProgress = true;
    while (needsRun) {
      needsRun = false;
      const files = Array.from(pendingFiles);
      pendingFiles.clear();
      const success = await runPipeline(config, dependencies.commandRunner, files);
      if (!success) {
        awaitingChangeAfterFailure = true;
        pendingFiles.clear();
        needsRun = false;
        break;
      }
    }
    runInProgress = false;
    if (pendingFiles.size > 0 && !awaitingChangeAfterFailure) {
      needsRun = true;
      triggerRun();
    }
  }

  dependencies.fileWatcher.start((filePath) => {
    enqueueChange(filePath);
  });

  return dependencies.fileWatcher;
}

function shouldTrack(filePath: string, config: ResolvedWatcherConfig): boolean {
  const ext = path.extname(filePath).toLowerCase();
  if (config.includeExtensions.length === 0) {
    return true;
  }
  return config.includeExtensions.includes(ext);
}

async function runPipeline(
  config: ResolvedWatcherConfig,
  commandRunner: CommandRunner,
  files: string[],
): Promise<boolean> {
  const description = files.length > 0 ? `${files.length} file(s)` : 'changes';
  console.log(`[${new Date().toISOString()}] Running pipeline for ${description}`);
  if (files.length > 0 && config.logChangedFiles) {
    files.forEach((file) => {
      console.log(`  • ${relativeToWorkspace(file, config.workspacePath)}`);
    });
  }
  try {
    await commandRunner.runInCompose(config.extractorCommand, 'repository-doc-extractor');
    if (config.validateCommand && config.validateCommand.length > 0) {
      await commandRunner.runInCompose(config.validateCommand, 'minerva validate');
    }
    await commandRunner.runInCompose(config.indexCommand, 'minerva index');
    console.log(`[${new Date().toISOString()}] Pipeline complete`);
    return true;
  } catch (error) {
    console.error(`[${new Date().toISOString()}] Pipeline failed: ${(error as Error).message}`);
    return false;
  }
}

function relativeToWorkspace(target: string, workspace: string): string {
  const relative = path.relative(workspace, target);
  return relative || path.basename(target);
}
