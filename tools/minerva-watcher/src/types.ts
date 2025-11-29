export interface WatcherConfigFile {
  workspacePath: string;
  composeDirectory?: string;
  composeCommand?: string[];
  serviceName?: string;
  extractorCommand: string[];
  validateCommand?: string[];
  indexCommand: string[];
  debounceMs?: number;
  includeExtensions?: string[];
  ignoreGlobs?: string[];
  logChangedFiles?: boolean;
}

export interface ResolvedWatcherConfig {
  workspacePath: string;
  composeDirectory: string;
  composeCommand: string[];
  serviceName: string;
  extractorCommand: string[];
  validateCommand?: string[];
  indexCommand: string[];
  debounceMs: number;
  includeExtensions: string[];
  ignoreGlobs: (string | RegExp)[];
  logChangedFiles: boolean;
}
