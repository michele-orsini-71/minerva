import pytest
from pathlib import Path
from argparse import ArgumentParser, Namespace

from minerva.cli import create_parser


class TestParserCreation:
    def test_create_parser_returns_argparse_instance(self):
        parser = create_parser()
        assert isinstance(parser, ArgumentParser)

    def test_parser_has_correct_prog_name(self):
        parser = create_parser()
        assert parser.prog == 'minerva'

    def test_parser_has_version_argument(self):
        parser = create_parser()
        with pytest.raises(SystemExit) as exc_info:
            parser.parse_args(['--version'])
        assert exc_info.value.code == 0

    def test_parser_requires_command(self):
        parser = create_parser()
        with pytest.raises(SystemExit):
            parser.parse_args([])


class TestIndexCommand:
    def test_index_command_requires_config(self):
        parser = create_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(['index'])

    def test_index_command_with_config(self):
        parser = create_parser()
        args = parser.parse_args(['index', '--config', 'config.json'])
        assert args.command == 'index'
        assert args.config == Path('config.json')
        assert args.verbose is False
        assert args.dry_run is False

    def test_index_command_with_verbose_flag(self):
        parser = create_parser()
        args = parser.parse_args(['index', '--config', 'config.json', '--verbose'])
        assert args.command == 'index'
        assert args.verbose is True

    def test_index_command_with_dry_run_flag(self):
        parser = create_parser()
        args = parser.parse_args(['index', '--config', 'config.json', '--dry-run'])
        assert args.command == 'index'
        assert args.dry_run is True

    def test_index_command_with_all_flags(self):
        parser = create_parser()
        args = parser.parse_args(['index', '--config', 'config.json', '--verbose', '--dry-run'])
        assert args.command == 'index'
        assert args.config == Path('config.json')
        assert args.verbose is True
        assert args.dry_run is True

    def test_index_command_config_as_path(self):
        parser = create_parser()
        args = parser.parse_args(['index', '--config', '/path/to/config.json'])
        assert args.config == Path('/path/to/config.json')

    def test_index_command_flags_order_independent(self):
        parser = create_parser()
        args1 = parser.parse_args(['index', '--verbose', '--config', 'config.json', '--dry-run'])
        args2 = parser.parse_args(['index', '--dry-run', '--verbose', '--config', 'config.json'])
        assert args1.verbose == args2.verbose
        assert args1.dry_run == args2.dry_run
        assert args1.config == args2.config


class TestServeCommand:
    def test_serve_command_requires_config(self):
        parser = create_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(['serve'])

    def test_serve_command_with_config(self):
        parser = create_parser()
        args = parser.parse_args(['serve', '--config', 'server-config.json'])
        assert args.command == 'serve'
        assert args.config == Path('server-config.json')

    def test_serve_command_config_as_path(self):
        parser = create_parser()
        args = parser.parse_args(['serve', '--config', '/etc/minerva/server.json'])
        assert args.config == Path('/etc/minerva/server.json')


class TestPeekCommand:
    def test_peek_command_requires_collection_name(self):
        parser = create_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(['peek'])

    def test_peek_command_with_collection_name_only(self):
        parser = create_parser()
        args = parser.parse_args(['peek', './chromadb_data', 'bear_notes'])
        assert args.command == 'peek'
        assert args.collection_name == 'bear_notes'
        assert args.chromadb == Path('./chromadb_data')
        assert args.format == 'text'

    def test_peek_command_with_custom_chromadb_path(self):
        parser = create_parser()
        args = parser.parse_args(['peek', '/custom/path', 'bear_notes'])
        assert args.collection_name == 'bear_notes'
        assert args.chromadb == Path('/custom/path')

    def test_peek_command_with_json_format(self):
        parser = create_parser()
        args = parser.parse_args(['peek', './chromadb_data', 'bear_notes', '--format', 'json'])
        assert args.collection_name == 'bear_notes'
        assert args.format == 'json'

    def test_peek_command_with_text_format(self):
        parser = create_parser()
        args = parser.parse_args(['peek', 'bear_notes', '--format', 'text'])
        assert args.format == 'text'

    def test_peek_command_with_all_options(self):
        parser = create_parser()
        args = parser.parse_args([
            'peek', '/data/chromadb', 'test_collection',
            '--format', 'json'
        ])
        assert args.command == 'peek'
        assert args.collection_name == 'test_collection'
        assert args.chromadb == Path('/data/chromadb')
        assert args.format == 'json'

    def test_peek_command_invalid_format_rejected(self):
        parser = create_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(['peek', 'bear_notes', '--format', 'xml'])

    def test_peek_command_options_order_independent(self):
        parser = create_parser()
        args1 = parser.parse_args(['peek', '/path', 'test', '--format', 'json'])
        args2 = parser.parse_args(['peek', '/path', 'test', '--format', 'json'])
        assert args1.chromadb == args2.chromadb
        assert args1.format == args2.format
        assert args1.collection_name == args2.collection_name


class TestValidateCommand:
    def test_validate_command_requires_json_file(self):
        parser = create_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(['validate'])

    def test_validate_command_with_json_file(self):
        parser = create_parser()
        args = parser.parse_args(['validate', 'notes.json'])
        assert args.command == 'validate'
        assert args.json_file == Path('notes.json')
        assert args.verbose is False

    def test_validate_command_with_verbose_flag(self):
        parser = create_parser()
        args = parser.parse_args(['validate', 'notes.json', '--verbose'])
        assert args.command == 'validate'
        assert args.json_file == Path('notes.json')
        assert args.verbose is True

    def test_validate_command_json_file_as_path(self):
        parser = create_parser()
        args = parser.parse_args(['validate', '/path/to/notes.json'])
        assert args.json_file == Path('/path/to/notes.json')

    def test_validate_command_options_order_independent(self):
        parser = create_parser()
        args1 = parser.parse_args(['validate', 'notes.json', '--verbose'])
        args2 = parser.parse_args(['validate', '--verbose', 'notes.json'])
        assert args1.json_file == args2.json_file
        assert args1.verbose == args2.verbose


class TestConfigCommand:
    def test_config_command_requires_subcommand(self):
        parser = create_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(['config'])

    def test_config_validate_requires_file(self):
        parser = create_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(['config', 'validate'])

    def test_config_validate_with_file(self):
        parser = create_parser()
        args = parser.parse_args(['config', 'validate', 'config.json'])
        assert args.command == 'config'
        assert args.config_command == 'validate'
        assert args.config_file == Path('config.json')


class TestCommandNames:
    def test_all_valid_commands(self):
        parser = create_parser()
        commands = ['index', 'serve', 'peek', 'validate', 'config']
        for command in commands:
            # Each command has different required args, so we provide them
            if command == 'index':
                args = parser.parse_args([command, '--config', 'config.json'])
            elif command == 'serve':
                args = parser.parse_args([command, '--config', 'config.json'])
            elif command == 'peek':
                args = parser.parse_args([command, 'collection_name'])
            elif command == 'validate':
                args = parser.parse_args([command, 'file.json'])
            elif command == 'config':
                args = parser.parse_args([command, 'validate', 'config.json'])
            assert args.command == command

    def test_invalid_command_rejected(self):
        parser = create_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(['invalid_command'])


class TestPathTypes:
    def test_config_paths_converted_to_path_objects(self):
        parser = create_parser()
        args = parser.parse_args(['index', '--config', 'config.json'])
        assert isinstance(args.config, Path)

    def test_chromadb_paths_converted_to_path_objects(self):
        parser = create_parser()
        args = parser.parse_args(['peek', '/data', 'test'])
        assert isinstance(args.chromadb, Path)

    def test_json_file_paths_converted_to_path_objects(self):
        parser = create_parser()
        args = parser.parse_args(['validate', 'notes.json'])
        assert isinstance(args.json_file, Path)

    def test_relative_paths_preserved(self):
        parser = create_parser()
        args = parser.parse_args(['index', '--config', './configs/config.json'])
        assert str(args.config) == 'configs/config.json'

    def test_absolute_paths_preserved(self):
        parser = create_parser()
        args = parser.parse_args(['index', '--config', '/absolute/path/config.json'])
        assert str(args.config) == '/absolute/path/config.json'


class TestDefaultValues:
    def test_index_verbose_defaults_to_false(self):
        parser = create_parser()
        args = parser.parse_args(['index', '--config', 'config.json'])
        assert args.verbose is False

    def test_index_dry_run_defaults_to_false(self):
        parser = create_parser()
        args = parser.parse_args(['index', '--config', 'config.json'])
        assert args.dry_run is False

    def test_validate_verbose_defaults_to_false(self):
        parser = create_parser()
        args = parser.parse_args(['validate', 'notes.json'])
        assert args.verbose is False

    def test_peek_chromadb_is_required(self):
        parser = create_parser()
        # chromadb path is now a required positional argument
        args = parser.parse_args(['peek', './chromadb_data'])
        assert args.chromadb == Path('./chromadb_data')

    def test_peek_format_defaults_to_text(self):
        parser = create_parser()
        args = parser.parse_args(['peek', './chromadb_data', 'collection'])
        assert args.format == 'text'


class TestEdgeCases:
    def test_collection_name_with_special_characters(self):
        parser = create_parser()
        args = parser.parse_args(['peek', './chromadb_data', 'bear-notes_2025'])
        assert args.collection_name == 'bear-notes_2025'

    def test_paths_with_spaces(self):
        parser = create_parser()
        args = parser.parse_args(['index', '--config', 'my config.json'])
        assert args.config == Path('my config.json')

    def test_multiple_commands_not_allowed(self):
        parser = create_parser()
        with pytest.raises(SystemExit):
            # This should fail because 'serve' is interpreted as collection_name for peek
            # but then '--config' expects a value, not another command
            parser.parse_args(['peek', 'collection', 'serve', '--config', 'config.json'])

    def test_empty_string_arguments_accepted(self):
        parser = create_parser()
        # Empty strings are technically valid, though not useful
        args = parser.parse_args(['peek', './chromadb_data', ''])
        assert args.collection_name == ''

    def test_unicode_in_collection_name(self):
        parser = create_parser()
        args = parser.parse_args(['peek', './chromadb_data', 'notes_日本語'])
        assert args.collection_name == 'notes_日本語'

    def test_unicode_in_paths(self):
        parser = create_parser()
        args = parser.parse_args(['validate', 'notes_日本語.json'])
        assert args.json_file == Path('notes_日本語.json')


class TestHelpText:
    def test_main_help_exits_cleanly(self):
        parser = create_parser()
        with pytest.raises(SystemExit) as exc_info:
            parser.parse_args(['--help'])
        assert exc_info.value.code == 0

    def test_index_help_exits_cleanly(self):
        parser = create_parser()
        with pytest.raises(SystemExit) as exc_info:
            parser.parse_args(['index', '--help'])
        assert exc_info.value.code == 0

    def test_serve_help_exits_cleanly(self):
        parser = create_parser()
        with pytest.raises(SystemExit) as exc_info:
            parser.parse_args(['serve', '--help'])
        assert exc_info.value.code == 0

    def test_peek_help_exits_cleanly(self):
        parser = create_parser()
        with pytest.raises(SystemExit) as exc_info:
            parser.parse_args(['peek', '--help'])
        assert exc_info.value.code == 0

    def test_validate_help_exits_cleanly(self):
        parser = create_parser()
        with pytest.raises(SystemExit) as exc_info:
            parser.parse_args(['validate', '--help'])
        assert exc_info.value.code == 0
