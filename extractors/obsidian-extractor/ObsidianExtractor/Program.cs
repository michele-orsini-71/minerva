using System.Text;
using System.Text.Json;
using System.Text.RegularExpressions;

return ObsidianExtractorApp.Run(args);

internal static class ObsidianExtractorApp
{
    private static readonly UTF8Encoding Utf8NoBom = new(encoderShouldEmitUTF8Identifier: false);
    private static readonly string[] MarkdownPatterns = ["*.md", "*.mdx", "*.markdown"];
    private static readonly string[] DefaultExcludes =
    [
        ".git",
        "node_modules",
        "__pycache__",
        ".venv",
        "venv",
        ".pytest_cache",
        ".obsidian"
    ];

    public static int Run(string[] args)
    {
        var parseResult = OptionsParser.TryParse(args, out var options, out var error, out var helpRequested);
        if (helpRequested)
        {
            OptionsParser.PrintUsage();
            return 0;
        }

        if (!parseResult || options is null)
        {
            if (!string.IsNullOrEmpty(error))
            {
                Console.Error.WriteLine(error);
            }

            OptionsParser.PrintUsage(Console.Error);
            return 1;
        }

        try
        {
            return options.ScanOnly ? RunScanOnly(options) : RunExtraction(options);
        }
        catch (DirectoryNotFoundException ex)
        {
            Console.Error.WriteLine($"Error: {ex.Message}");
            return 1;
        }
        catch (IOException ex)
        {
            Console.Error.WriteLine($"IO error: {ex.Message}");
            return 1;
        }
        catch (UnauthorizedAccessException ex)
        {
            Console.Error.WriteLine($"Permission error: {ex.Message}");
            return 1;
        }
        catch (Exception ex)
        {
            Console.Error.WriteLine($"Unexpected error: {ex.Message}");
            return 1;
        }
    }

    private static int RunScanOnly(Options options)
    {
        if (options.OutputPath is not null)
        {
            Console.Error.WriteLine("Warning: --scan-only ignores -o/--output. Results will print to stdout.");
        }

        var root = ValidateRootDirectory(options.DirectoryPath);
        if (options.Verbose)
        {
            Console.Error.WriteLine($"Scanning directory: {root}");
            if (options.ExcludePatterns.Count > 0)
            {
                Console.Error.WriteLine($"Excluding patterns: {string.Join(", ", options.ExcludePatterns)}");
            }
        }

        var excludeSet = CreateExcludeSet(options.ExcludePatterns);
        var markdownFiles = EnumerateMarkdownFiles(root, excludeSet);
        var directories = new SortedSet<string>(StringComparer.Ordinal);

        foreach (var file in markdownFiles)
        {
            var directory = Path.GetDirectoryName(file) ?? root;
            var relative = GetRelativePathOrSelf(root, directory);
            directories.Add(relative);
        }

        foreach (var directory in directories)
        {
            Console.WriteLine(directory);
        }

        if (options.Verbose)
        {
            Console.Error.WriteLine($"\u2713 Found {directories.Count} unique directory path(s)");
        }

        return 0;
    }

    private static int RunExtraction(Options options)
    {
        var root = ValidateRootDirectory(options.DirectoryPath);
        if (options.Verbose)
        {
            Console.Error.WriteLine($"Scanning directory: {root}");
            if (options.ExcludePatterns.Count > 0)
            {
                Console.Error.WriteLine($"Excluding patterns: {string.Join(", ", options.ExcludePatterns)}");
            }
        }

        var excludeSet = CreateExcludeSet(options.ExcludePatterns);
        var markdownFiles = EnumerateMarkdownFiles(root, excludeSet);
        var notes = new List<Note>();

        foreach (var file in markdownFiles)
        {
            try
            {
                notes.Add(ParseMarkdownFile(file, root));
            }
            catch (Exception ex)
            {
                Console.Error.WriteLine($"Warning: Skipping {file}: {ex.Message}");
            }
        }

        if (notes.Count == 0)
        {
            Console.Error.WriteLine($"Error: No markdown files found in {root}");
            return 1;
        }

        var serializerOptions = new JsonSerializerOptions
        {
            WriteIndented = true,
            PropertyNamingPolicy = JsonNamingPolicy.CamelCase
        };

        var payload = JsonSerializer.Serialize(notes, serializerOptions);
        if (options.OutputPath is not null)
        {
            var resolvedOutput = Path.GetFullPath(options.OutputPath);
            var directory = Path.GetDirectoryName(resolvedOutput);
            if (!string.IsNullOrEmpty(directory))
            {
                Directory.CreateDirectory(directory);
            }

            File.WriteAllText(resolvedOutput, payload + Environment.NewLine, Utf8NoBom);
        }
        else
        {
            Console.Out.WriteLine(payload);
        }

        if (options.Verbose)
        {
            Console.Error.WriteLine($"\u2713 Exported {notes.Count} markdown file(s)");
        }

        return 0;
    }

    private static string ValidateRootDirectory(string directoryPath)
    {
        var root = Path.GetFullPath(directoryPath);
        if (!Directory.Exists(root))
        {
            throw new DirectoryNotFoundException($"Directory not found: {directoryPath}");
        }

        return root;
    }

    private static HashSet<string> CreateExcludeSet(IReadOnlyCollection<string> custom)
    {
        var set = new HashSet<string>(DefaultExcludes, StringComparer.OrdinalIgnoreCase);
        foreach (var pattern in custom)
        {
            if (!string.IsNullOrWhiteSpace(pattern))
            {
                set.Add(pattern.Trim());
            }
        }

        return set;
    }

    private static List<string> EnumerateMarkdownFiles(string root, HashSet<string> excludeSet)
    {
        var results = new HashSet<string>(StringComparer.Ordinal);
        foreach (var pattern in MarkdownPatterns)
        {
            foreach (var file in Directory.EnumerateFiles(root, pattern, SearchOption.AllDirectories))
            {
                if (ShouldExclude(file, excludeSet))
                {
                    continue;
                }

                results.Add(Path.GetFullPath(file));
            }
        }

        return results.OrderBy(path => path, StringComparer.Ordinal).ToList();
    }

    private static bool ShouldExclude(string fullPath, HashSet<string> excludeSet)
    {
        var normalized = fullPath.Replace(Path.AltDirectorySeparatorChar, Path.DirectorySeparatorChar);
        foreach (var part in normalized.Split(Path.DirectorySeparatorChar, StringSplitOptions.RemoveEmptyEntries))
        {
            if (excludeSet.Contains(part))
            {
                return true;
            }
        }

        return false;
    }

    private static Note ParseMarkdownFile(string filePath, string root)
    {
        var content = File.ReadAllText(filePath, Encoding.UTF8);
        var title = ExtractTitle(content, filePath);
        var info = new FileInfo(filePath);
        var modifiedUtc = info.LastWriteTimeUtc;
        var createdUtc = info.CreationTimeUtc;

        if (createdUtc == DateTime.MinValue)
        {
            createdUtc = modifiedUtc;
        }

        return new Note
        {
            Title = title,
            Markdown = content,
            Size = Encoding.UTF8.GetByteCount(content),
            ModificationDate = FormatIsoTimestamp(modifiedUtc),
            CreationDate = FormatIsoTimestamp(createdUtc),
            SourcePath = GetRelativePathOrSelf(root, filePath)
        };
    }

    private static string ExtractTitle(string markdown, string filePath)
    {
        var headingMatch = Regex.Match(markdown, @"^\s*#\s+(.+)$", RegexOptions.Multiline);
        if (headingMatch.Success)
        {
            var heading = headingMatch.Groups[1].Value.Trim();
            if (!string.IsNullOrEmpty(heading))
            {
                return heading;
            }
        }

        var fileName = Path.GetFileNameWithoutExtension(filePath);
        return string.IsNullOrWhiteSpace(fileName) ? Path.GetFileName(filePath) : fileName;
    }

    private static string FormatIsoTimestamp(DateTime dateTimeUtc)
    {
        var utc = dateTimeUtc.Kind == DateTimeKind.Utc ? dateTimeUtc : dateTimeUtc.ToUniversalTime();
        return utc.ToString("yyyy-MM-dd'T'HH:mm:ss'Z'");
    }

    private static string GetRelativePathOrSelf(string root, string path)
    {
        var relative = Path.GetRelativePath(root, path);
        if (relative == "." || string.IsNullOrEmpty(relative))
        {
            return ".";
        }

        return NormalizeSeparators(relative);
    }

    private static string NormalizeSeparators(string path)
    {
        return path.Replace(Path.DirectorySeparatorChar, '/').Replace(Path.AltDirectorySeparatorChar, '/');
    }

    private sealed class Note
    {
        public required string Title { get; init; }
        public required string Markdown { get; init; }
        public required int Size { get; init; }
        public required string ModificationDate { get; init; }
        public required string CreationDate { get; init; }
        public required string SourcePath { get; init; }
    }
}

internal static class OptionsParser
{
    public static bool TryParse(string[] args, out Options? options, out string? error, out bool helpRequested)
    {
        options = null;
        error = null;
        helpRequested = false;

        if (args.Length == 0)
        {
            error = "Missing directory argument.";
            return false;
        }

        var directoryPath = string.Empty;
        var excludePatterns = new List<string>();
        string? outputPath = null;
        var verbose = false;
        var scanOnly = false;

        for (var i = 0; i < args.Length; i++)
        {
            var token = args[i];
            switch (token)
            {
                case "-h":
                case "--help":
                    helpRequested = true;
                    return false;
                case "-v":
                case "--verbose":
                    verbose = true;
                    break;
                case "--scan-only":
                    scanOnly = true;
                    break;
                case "--exclude":
                    if (i + 1 >= args.Length)
                    {
                        error = "--exclude requires a pattern argument.";
                        return false;
                    }

                    excludePatterns.Add(args[++i]);
                    break;
                case "-o":
                case "--output":
                    if (i + 1 >= args.Length)
                    {
                        error = "-o/--output requires a file path.";
                        return false;
                    }

                    outputPath = args[++i];
                    break;
                default:
                    if (token.StartsWith("-"))
                    {
                        error = $"Unknown option: {token}";
                        return false;
                    }

                    if (!string.IsNullOrEmpty(directoryPath))
                    {
                        error = "Multiple directories provided. Only one root path is allowed.";
                        return false;
                    }

                    directoryPath = token;
                    break;
            }
        }

        if (string.IsNullOrEmpty(directoryPath))
        {
            error = "Directory argument is required.";
            return false;
        }

        options = new Options(directoryPath, outputPath, verbose, scanOnly, excludePatterns);
        return true;
    }

    public static void PrintUsage(TextWriter? writer = null)
    {
        writer ??= Console.Out;
        writer.WriteLine("Usage: obsidian-extractor <directory> [options]");
        writer.WriteLine();
        writer.WriteLine("Options:");
        writer.WriteLine("  -o, --output <file>      Write JSON output to file (defaults to stdout)");
        writer.WriteLine("  -v, --verbose           Print progress information to stderr");
        writer.WriteLine("      --exclude <pattern>  Exclude directories matching name (repeatable)");
        writer.WriteLine("      --scan-only          List directories containing markdown files without exporting");
        writer.WriteLine("  -h, --help              Show this message");
    }
}

internal sealed record Options(
    string DirectoryPath,
    string? OutputPath,
    bool Verbose,
    bool ScanOnly,
    IReadOnlyList<string> ExcludePatterns
);
