import chokidar from 'chokidar';

export type FileChangeType = 'add' | 'change' | 'unlink';
export type FileChangeCallback = (filePath: string, eventType: FileChangeType) => void;

/**
 * Abstract interface for file watching.
 * Allows dependency injection and testing with fake implementations.
 */
export interface FileWatcher {
  /**
   * Start watching for file changes
   * @param callback Function to call when files change
   */
  start(callback: FileChangeCallback): void;

  /**
   * Stop watching and clean up resources
   */
  close(): Promise<void>;
}

/**
 * Production implementation using chokidar
 */
export class ChokidarFileWatcher implements FileWatcher {
  private watcher: chokidar.FSWatcher | null = null;

  constructor(
    private watchPath: string,
    private options: chokidar.WatchOptions,
  ) {}

  start(callback: FileChangeCallback): void {
    if (this.watcher) {
      throw new Error('Watcher already started');
    }

    this.watcher = chokidar.watch(this.watchPath, this.options);
    this.watcher.on('add', (path) => callback(path, 'add'));
    this.watcher.on('change', (path) => callback(path, 'change'));
    this.watcher.on('unlink', (path) => callback(path, 'unlink'));
  }

  async close(): Promise<void> {
    if (this.watcher) {
      await this.watcher.close();
      this.watcher = null;
    }
  }
}

/**
 * Fake implementation for unit tests.
 * Allows programmatic simulation of file system events.
 */
export class FakeFileWatcher implements FileWatcher {
  private callback: FileChangeCallback | null = null;
  private started = false;

  start(callback: FileChangeCallback): void {
    this.callback = callback;
    this.started = true;
  }

  async close(): Promise<void> {
    this.started = false;
    this.callback = null;
  }

  /**
   * Simulate a file addition event
   */
  fireAdd(filePath: string): void {
    if (!this.started) {
      throw new Error('Watcher not started');
    }
    if (this.callback) {
      this.callback(filePath, 'add');
    }
  }

  /**
   * Simulate a file change event
   */
  fireChange(filePath: string): void {
    if (!this.started) {
      throw new Error('Watcher not started');
    }
    if (this.callback) {
      this.callback(filePath, 'change');
    }
  }

  /**
   * Simulate a file deletion event
   */
  fireUnlink(filePath: string): void {
    if (!this.started) {
      throw new Error('Watcher not started');
    }
    if (this.callback) {
      this.callback(filePath, 'unlink');
    }
  }
}
