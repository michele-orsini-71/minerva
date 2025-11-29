import { spawn } from 'child_process';
import { ResolvedWatcherConfig } from './types';
import { boolean } from 'yargs';

/**
 * Abstract interface for running commands.
 * Allows dependency injection and testing with dry-run implementations.
 */
export interface CommandRunner {
  /**
   * Run a command in the compose environment
   * @param command The command to run
   * @param label Human-readable label for logging
   * @returns Promise that resolves when command completes successfully
   */
  runInCompose(command: string[], label: string): Promise<void>;
}

export function getCommandRunner(dryRun: boolean, config: ResolvedWatcherConfig): CommandRunner {
  if (dryRun) {
    return new DryRunCommandRunner(config);
  } else {
    return new RealCommandRunner(config);
  }
}

/**
 * Production implementation that actually executes commands
 */
export class RealCommandRunner implements CommandRunner {
  constructor(private config: ResolvedWatcherConfig) {}

  async runInCompose(command: string[], label: string): Promise<void> {
    const [executable, ...baseArgs] = this.config.composeCommand;
    const args = [...baseArgs, 'run', '--rm', this.config.serviceName, ...command];
    await this.spawnWithLogging(executable, args, this.config.composeDirectory, label);
  }

  private spawnWithLogging(
    command: string,
    args: string[],
    cwd: string,
    label: string,
  ): Promise<void> {
    return new Promise((resolve, reject) => {
      const start = Date.now();
      console.log(`[${new Date().toISOString()}] ${label} started`);
      const child = spawn(command, args, { cwd, stdio: 'inherit' });
      child.on('error', (error) => {
        console.error(`[${new Date().toISOString()}] ${label} failed: ${error.message}`);
        reject(error);
      });
      child.on('exit', (code) => {
        if (code === 0) {
          const duration = ((Date.now() - start) / 1000).toFixed(1);
          console.log(`[${new Date().toISOString()}] ${label} finished in ${duration}s`);
          resolve();
        } else {
          console.error(`[${new Date().toISOString()}] ${label} exited with code ${code}`);
          reject(new Error(`${label} exited with code ${code}`));
        }
      });
    });
  }
}

/**
 * Dry-run implementation that logs commands instead of executing them
 */
export class DryRunCommandRunner implements CommandRunner {
  constructor(private config: ResolvedWatcherConfig) {}

  async runInCompose(command: string[], label: string): Promise<void> {
    const [executable, ...baseArgs] = this.config.composeCommand;
    const args = [...baseArgs, 'run', '--rm', this.config.serviceName, ...command];
    const fullCommand = [executable, ...args].join(' ');

    console.log(`[DRY-RUN] ${label}`);
    console.log(`  Command: ${fullCommand}`);
    console.log(`  Working directory: ${this.config.composeDirectory}`);

    // Simulate a short delay
    await new Promise(resolve => setTimeout(resolve, 100));
  }
}

/**
 * Fake implementation for unit tests
 */
export class FakeCommandRunner implements CommandRunner {
  public executedCommands: Array<{ command: string[]; label: string }> = [];
  public shouldFail = false;

  async runInCompose(command: string[], label: string): Promise<void> {
    this.executedCommands.push({ command, label });

    if (this.shouldFail) {
      throw new Error(`Fake command failed: ${label}`);
    }

    // Simulate async execution
    await new Promise(resolve => setTimeout(resolve, 10));
  }

  reset(): void {
    this.executedCommands = [];
    this.shouldFail = false;
  }
}
