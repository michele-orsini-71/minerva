import path from 'path';
import { startWatcher, WatcherDependencies } from './watcher';
import { FakeFileWatcher } from './fileWatcher';
import { FakeCommandRunner } from './commandRunner';
import { ResolvedWatcherConfig } from './types';

function createTestConfig(overrides?: Partial<ResolvedWatcherConfig>): ResolvedWatcherConfig {
  return {
    workspacePath: '/test/workspace',
    composeDirectory: '/test/compose',
    composeCommand: ['docker', 'compose'],
    serviceName: 'minerva',
    extractorCommand: ['repository-doc-extractor'],
    validateCommand: ['minerva', 'validate'],
    indexCommand: ['minerva', 'index'],
    debounceMs: 100,
    includeExtensions: ['.md'],
    ignoreGlobs: ['**/.git/**'],
    logChangedFiles: false,
    ...overrides,
  };
}

function createTestDependencies() {
  const fileWatcher = new FakeFileWatcher();
  const commandRunner = new FakeCommandRunner();
  const dependencies: WatcherDependencies = {
    fileWatcher,
    commandRunner,
  };
  return {
    dependencies,
    fileWatcher,
    commandRunner,
  };
}

async function wait(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms));
}

describe('Watcher', () => {
  describe('File tracking', () => {
    it('should track files with included extensions', async () => {
      const config = createTestConfig({ includeExtensions: ['.md'] });
      const { dependencies, fileWatcher, commandRunner } = createTestDependencies();

      startWatcher(config, dependencies);
      fileWatcher.fireChange('/test/workspace/doc.md');

      await wait(150); // Wait for debounce

      expect(commandRunner.executedCommands.length).toBeGreaterThan(0);
    });

    it('should ignore files without included extensions', async () => {
      const config = createTestConfig({ includeExtensions: ['.md'] });
      const { dependencies, fileWatcher, commandRunner } = createTestDependencies();

      startWatcher(config, dependencies);
      fileWatcher.fireChange('/test/workspace/code.js');

      await wait(150); // Wait for debounce

      expect(commandRunner.executedCommands.length).toBe(0);
    });

    it('should track all files when includeExtensions is empty', async () => {
      const config = createTestConfig({ includeExtensions: [] });
      const { dependencies, fileWatcher, commandRunner } = createTestDependencies();

      startWatcher(config, dependencies);
      fileWatcher.fireChange('/test/workspace/any-file.xyz');

      await wait(150); // Wait for debounce

      expect(commandRunner.executedCommands.length).toBeGreaterThan(0);
    });

    it('should handle add events', async () => {
      const config = createTestConfig();
      const { dependencies, fileWatcher, commandRunner } = createTestDependencies();

      startWatcher(config, dependencies);
      fileWatcher.fireAdd('/test/workspace/new.md');

      await wait(150);

      expect(commandRunner.executedCommands.length).toBeGreaterThan(0);
    });

    it('should handle unlink events', async () => {
      const config = createTestConfig();
      const { dependencies, fileWatcher, commandRunner } = createTestDependencies();

      startWatcher(config, dependencies);
      fileWatcher.fireUnlink('/test/workspace/deleted.md');

      await wait(150);

      expect(commandRunner.executedCommands.length).toBeGreaterThan(0);
    });
  });

  describe('Debouncing', () => {
    it('should debounce multiple rapid changes', async () => {
      const config = createTestConfig({ debounceMs: 100 });
      const { dependencies, fileWatcher, commandRunner } = createTestDependencies();

      startWatcher(config, dependencies);

      // Fire multiple changes rapidly
      fileWatcher.fireChange('/test/workspace/file1.md');
      fileWatcher.fireChange('/test/workspace/file2.md');
      fileWatcher.fireChange('/test/workspace/file3.md');

      // Should not run yet
      expect(commandRunner.executedCommands.length).toBe(0);

      await wait(150); // Wait for debounce

      // Should run only once
      expect(commandRunner.executedCommands.length).toBe(3); // extractor, validate, index
    });

    it('should reset debounce timer on new changes', async () => {
      const config = createTestConfig({ debounceMs: 100 });
      const { dependencies, fileWatcher, commandRunner } = createTestDependencies();

      startWatcher(config, dependencies);

      fileWatcher.fireChange('/test/workspace/file1.md');
      await wait(50); // Half debounce time

      fileWatcher.fireChange('/test/workspace/file2.md');
      await wait(50); // Another half

      // Should still not have run because timer was reset
      expect(commandRunner.executedCommands.length).toBe(0);

      await wait(100); // Complete the debounce

      expect(commandRunner.executedCommands.length).toBe(3);
    });
  });

  describe('Pipeline execution', () => {
    it('should run extractor, validate, and index commands in order', async () => {
      const config = createTestConfig();
      const { dependencies, fileWatcher, commandRunner } = createTestDependencies();

      startWatcher(config, dependencies);
      fileWatcher.fireChange('/test/workspace/test.md');

      await wait(150);

      expect(commandRunner.executedCommands).toHaveLength(3);
      expect(commandRunner.executedCommands[0].label).toBe('repository-doc-extractor');
      expect(commandRunner.executedCommands[1].label).toBe('minerva validate');
      expect(commandRunner.executedCommands[2].label).toBe('minerva index');
    });

    it('should skip validate if not configured', async () => {
      const config = createTestConfig({ validateCommand: undefined });
      const { dependencies, fileWatcher, commandRunner } = createTestDependencies();

      startWatcher(config, dependencies);
      fileWatcher.fireChange('/test/workspace/test.md');

      await wait(150);

      expect(commandRunner.executedCommands).toHaveLength(2);
      expect(commandRunner.executedCommands[0].label).toBe('repository-doc-extractor');
      expect(commandRunner.executedCommands[1].label).toBe('minerva index');
    });

    it('should use correct commands from config', async () => {
      const config = createTestConfig({
        extractorCommand: ['custom-extractor', '--flag'],
        indexCommand: ['custom-index', '--verbose'],
      });
      const { dependencies, fileWatcher, commandRunner } = createTestDependencies();

      startWatcher(config, dependencies);
      fileWatcher.fireChange('/test/workspace/test.md');

      await wait(150);

      expect(commandRunner.executedCommands[0].command).toEqual(['custom-extractor', '--flag']);
      expect(commandRunner.executedCommands[2].command).toEqual(['custom-index', '--verbose']);
    });
  });

  describe('Error handling', () => {
    it('should stop pipeline on first error', async () => {
      const config = createTestConfig();
      const { dependencies, fileWatcher, commandRunner } = createTestDependencies();

      commandRunner.shouldFail = true;

      startWatcher(config, dependencies);
      fileWatcher.fireChange('/test/workspace/test.md');

      await wait(150);

      // Should only attempt first command
      expect(commandRunner.executedCommands).toHaveLength(1);
      expect(commandRunner.executedCommands[0].label).toBe('repository-doc-extractor');
    });

    it('should wait for new change after failure before retrying', async () => {
      const config = createTestConfig();
      const { dependencies, fileWatcher, commandRunner } = createTestDependencies();

      commandRunner.shouldFail = true;

      startWatcher(config, dependencies);
      fileWatcher.fireChange('/test/workspace/test.md');

      await wait(150);

      expect(commandRunner.executedCommands).toHaveLength(1);

      // Fix the issue
      commandRunner.shouldFail = false;
      commandRunner.reset();

      // Without a new change, nothing should happen
      await wait(150);
      expect(commandRunner.executedCommands).toHaveLength(0);

      // Fire a new change to recover
      fileWatcher.fireChange('/test/workspace/test.md');
      await wait(150);

      // Should successfully complete pipeline now
      expect(commandRunner.executedCommands).toHaveLength(3);
    });

    it('should clear pending files after failure', async () => {
      const config = createTestConfig();
      const { dependencies, fileWatcher, commandRunner } = createTestDependencies();

      commandRunner.shouldFail = true;

      startWatcher(config, dependencies);

      // Queue multiple changes
      fileWatcher.fireChange('/test/workspace/file1.md');
      fileWatcher.fireChange('/test/workspace/file2.md');
      fileWatcher.fireChange('/test/workspace/file3.md');

      await wait(150);

      // Should fail and clear queue
      expect(commandRunner.executedCommands).toHaveLength(1);

      commandRunner.shouldFail = false;
      commandRunner.reset();

      // New change should trigger fresh run
      fileWatcher.fireChange('/test/workspace/new.md');
      await wait(150);

      expect(commandRunner.executedCommands).toHaveLength(3);
    });
  });

  describe('Concurrent execution prevention', () => {
    it('should not start new run while one is in progress', async () => {
      const config = createTestConfig();
      const { dependencies, fileWatcher, commandRunner } = createTestDependencies();

      startWatcher(config, dependencies);

      // Fire first change
      fileWatcher.fireChange('/test/workspace/file1.md');
      await wait(150);

      // While pipeline is running (commandRunner has async delay), fire another change
      fileWatcher.fireChange('/test/workspace/file2.md');

      await wait(200); // Wait for everything to settle

      // Should have run twice (first run: 3 commands, second run: 3 commands)
      // The second change should trigger a new run after the first completes
      expect(commandRunner.executedCommands.length).toBeGreaterThanOrEqual(3);
    });
  });

  describe('Multiple file batching', () => {
    it('should batch multiple file changes into single pipeline run', async () => {
      const config = createTestConfig();
      const { dependencies, fileWatcher, commandRunner } = createTestDependencies();

      startWatcher(config, dependencies);

      // Fire multiple changes rapidly
      fileWatcher.fireChange('/test/workspace/file1.md');
      fileWatcher.fireChange('/test/workspace/file2.md');
      fileWatcher.fireChange('/test/workspace/file3.md');

      await wait(150);

      // Should run pipeline once with all files
      expect(commandRunner.executedCommands).toHaveLength(3);
    });
  });
});
