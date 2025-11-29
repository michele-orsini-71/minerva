import fs from 'fs';
import path from 'path';
import { ResolvedWatcherConfig, WatcherConfigFile } from './types';

const defaultIgnoreGlobs = ['**/.git/**', '**/node_modules/**', '**/.venv/**', '**/__pycache__/**'];
const defaultExtensions = ['.md', '.mdx'];

export function loadConfig(configPath: string): ResolvedWatcherConfig {
  const resolvedPath = path.resolve(configPath);
  const payload = fs.readFileSync(resolvedPath, 'utf8');
  let raw: WatcherConfigFile;
  try {
    raw = JSON.parse(payload);
  } catch (error) {
    throw new Error(`Failed to parse config: ${(error as Error).message}`);
  }

  const workspacePath = ensureAbsolute(raw.workspacePath, path.dirname(resolvedPath), 'workspacePath');
  const composeDirectory = resolvePath(raw.composeDirectory ?? process.cwd(), path.dirname(resolvedPath));
  const composeCommand = normalizeCommand(raw.composeCommand ?? ['docker', 'compose']);
  const extractorCommand = requireCommand(raw.extractorCommand, 'extractorCommand');
  const validateCommand = raw.validateCommand ? requireCommand(raw.validateCommand, 'validateCommand') : undefined;
  const indexCommand = requireCommand(raw.indexCommand, 'indexCommand');
  const debounceMs = raw.debounceMs && raw.debounceMs > 0 ? raw.debounceMs : 2000;
  const includeExtensions = normalizeExtensions(raw.includeExtensions ?? defaultExtensions);
  const ignoreGlobs = normalizeIgnore(raw.ignoreGlobs ?? defaultIgnoreGlobs);
  const logChangedFiles = Boolean(raw.logChangedFiles);

  return {
    workspacePath,
    composeDirectory,
    composeCommand,
    serviceName: raw.serviceName?.trim() || 'minerva',
    extractorCommand,
    validateCommand,
    indexCommand,
    debounceMs,
    includeExtensions,
    ignoreGlobs,
    logChangedFiles,
  };
}

function ensureAbsolute(input: string | undefined, baseDir: string, field: string): string {
  if (!input) {
    throw new Error(`Missing required field: ${field}`);
  }
  return resolvePath(input, baseDir);
}

function resolvePath(target: string, baseDir: string): string {
  return path.isAbsolute(target) ? target : path.resolve(baseDir, target);
}

function normalizeCommand(value: string[]): string[] {
  if (!Array.isArray(value) || value.length === 0) {
    throw new Error('composeCommand must be a non-empty array of strings');
  }
  value.forEach((part, index) => {
    if (typeof part !== 'string' || !part.trim()) {
      throw new Error(`composeCommand[${index}] must be a non-empty string`);
    }
  });
  return value.map((part) => part.trim());
}

function requireCommand(value: string[] | undefined, field: string): string[] {
  if (!Array.isArray(value) || value.length === 0) {
    throw new Error(`Missing required non-empty array: ${field}`);
  }
  value.forEach((part, index) => {
    if (typeof part !== 'string' || !part.trim()) {
      throw new Error(`${field}[${index}] must be a non-empty string`);
    }
  });
  return value.map((part) => part.trim());
}

function normalizeExtensions(values: string[]): string[] {
  return values.map((item) => {
    const trimmed = item.trim().toLowerCase();
    if (!trimmed) {
      throw new Error('includeExtensions entries cannot be empty');
    }
    return trimmed.startsWith('.') ? trimmed : `.${trimmed}`;
  });
}

function normalizeIgnore(values: string[]): (string | RegExp)[] {
  return values.map((value) => {
    if (value.startsWith('regex:')) {
      const pattern = value.slice('regex:'.length);
      return new RegExp(pattern);
    }
    return value;
  });
}
