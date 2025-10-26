import pytest
import sys
import importlib


class TestCoreModuleImports:
    def test_import_cli_module(self):
        import minerva.cli
        assert hasattr(minerva.cli, 'main')
        assert hasattr(minerva.cli, 'create_parser')

    def test_import_main_module(self):
        import minerva.__main__
        assert minerva.__main__ is not None

    def test_import_minerva_package(self):
        import minerva
        assert minerva.__name__ == 'minerva'


class TestCommandModuleImports:
    def test_import_index_command(self):
        from minerva.commands.index import run_index
        assert callable(run_index)

    def test_import_serve_command(self):
        from minerva.commands.serve import run_serve
        assert callable(run_serve)

    def test_import_peek_command(self):
        from minerva.commands.peek import run_peek
        assert callable(run_peek)

    def test_import_validate_command(self):
        from minerva.commands.validate import run_validate
        assert callable(run_validate)

    def test_import_commands_package(self):
        import minerva.commands
        assert minerva.commands.__name__ == 'minerva.commands'


class TestCommonModuleImports:
    def test_import_schemas_module(self):
        from minerva.common.schemas import (
            validate_note,
            validate_notes_array,
            validate_notes_file,
            NOTE_SCHEMA,
            NOTES_ARRAY_SCHEMA
        )
        assert callable(validate_note)
        assert callable(validate_notes_array)
        assert callable(validate_notes_file)
        assert isinstance(NOTE_SCHEMA, dict)
        assert isinstance(NOTES_ARRAY_SCHEMA, dict)

    def test_import_logger_module(self):
        from minerva.common.logger import get_logger, ConsoleLogger
        assert callable(get_logger)
        assert ConsoleLogger is not None

    def test_import_config_module(self):
        from minerva.common.config import load_config
        assert callable(load_config)

    def test_import_ai_provider_module(self):
        from minerva.common.ai_provider import AIProvider, AIProviderConfig
        assert AIProvider is not None
        assert AIProviderConfig is not None

    def test_import_common_package(self):
        import minerva.common
        assert minerva.common.__name__ == 'minerva.common'


class TestIndexingModuleImports:
    def test_import_chunking_module(self):
        from minerva.indexing.chunking import create_chunks_from_notes
        assert callable(create_chunks_from_notes)

    def test_import_embeddings_module(self):
        from minerva.indexing.embeddings import generate_embeddings
        assert callable(generate_embeddings)

    def test_import_storage_module(self):
        from minerva.indexing.storage import (
            initialize_chromadb_client,
            insert_chunks
        )
        assert callable(initialize_chromadb_client)
        assert callable(insert_chunks)

    def test_import_json_loader_module(self):
        from minerva.indexing.json_loader import load_json_notes
        assert callable(load_json_notes)

    def test_import_indexing_package(self):
        import minerva.indexing
        assert minerva.indexing.__name__ == 'minerva.indexing'


class TestServerModuleImports:
    def test_import_mcp_server_module(self):
        from minerva.server.mcp_server import main, initialize_server
        assert callable(main)
        assert callable(initialize_server)

    def test_import_search_tools_module(self):
        from minerva.server.search_tools import search_knowledge_base
        assert callable(search_knowledge_base)

    def test_import_collection_discovery_module(self):
        from minerva.server.collection_discovery import list_collections
        assert callable(list_collections)

    def test_import_context_retrieval_module(self):
        from minerva.server.context_retrieval import get_enhanced_content
        assert callable(get_enhanced_content)

    def test_import_startup_validation_module(self):
        from minerva.server.startup_validation import validate_server_prerequisites
        assert callable(validate_server_prerequisites)

    def test_import_server_package(self):
        import minerva.server
        assert minerva.server.__name__ == 'minerva.server'


class TestNoCircularImports:
    def test_cli_imports_dont_create_cycles(self):
        import minerva.cli
        # If we get here without ImportError, no circular imports
        assert True

    def test_commands_imports_dont_create_cycles(self):
        from minerva.commands import index, serve, peek, validate
        assert True

    def test_common_imports_dont_create_cycles(self):
        from minerva.common import schemas, logger, config, ai_provider
        assert True

    def test_indexing_imports_dont_create_cycles(self):
        from minerva.indexing import chunking, embeddings, storage, json_loader
        assert True

    def test_server_imports_dont_create_cycles(self):
        from minerva.server import (
            mcp_server,
            search_tools,
            collection_discovery,
            context_retrieval,
            startup_validation
        )
        assert True


class TestCrossModuleImports:
    def test_commands_can_import_from_common(self):
        from minerva.commands.index import run_index
        from minerva.common.logger import get_logger
        # Both imports should work without conflict
        assert callable(run_index)
        assert callable(get_logger)

    def test_commands_can_import_from_indexing(self):
        from minerva.commands.index import run_index
        from minerva.indexing.chunking import create_chunks_from_notes
        assert callable(run_index)
        assert callable(create_chunks_from_notes)

    def test_commands_can_import_from_server(self):
        from minerva.commands.serve import run_serve
        from minerva.server.mcp_server import main
        assert callable(run_serve)
        assert callable(main)

    def test_indexing_can_import_from_common(self):
        from minerva.indexing.embeddings import generate_embeddings
        from minerva.common.ai_provider import AIProvider
        assert callable(generate_embeddings)
        assert AIProvider is not None

    def test_server_can_import_from_common(self):
        from minerva.server.mcp_server import main
        from minerva.common.logger import get_logger
        assert callable(main)
        assert callable(get_logger)


class TestModuleAttributes:
    def test_cli_has_main_function(self):
        from minerva import cli
        assert hasattr(cli, 'main')
        assert callable(cli.main)

    def test_schemas_has_validation_functions(self):
        from minerva.common import schemas
        assert hasattr(schemas, 'validate_note')
        assert hasattr(schemas, 'validate_notes_array')
        assert hasattr(schemas, 'validate_notes_file')

    def test_logger_has_get_logger_function(self):
        from minerva.common import logger
        assert hasattr(logger, 'get_logger')
        assert callable(logger.get_logger)

    def test_chunking_has_create_chunks_function(self):
        from minerva.indexing import chunking
        assert hasattr(chunking, 'create_chunks_from_notes')
        assert callable(chunking.create_chunks_from_notes)

    def test_storage_has_chromadb_functions(self):
        from minerva.indexing import storage
        assert hasattr(storage, 'initialize_chromadb_client')
        assert hasattr(storage, 'insert_chunks')


class TestReimports:
    def test_reimport_same_module_returns_same_object(self):
        import minerva.common.schemas as schemas1
        import minerva.common.schemas as schemas2
        assert schemas1 is schemas2

    def test_reimport_after_deletion(self):
        import minerva.common.logger
        module_id = id(minerva.common.logger)
        # Reimport should work
        import minerva.common.logger as logger2
        assert logger2 is not None


class TestPackageStructure:
    def test_minerva_is_package(self):
        import minerva
        assert hasattr(minerva, '__path__')

    def test_commands_is_subpackage(self):
        import minerva.commands
        assert hasattr(minerva.commands, '__path__')

    def test_common_is_subpackage(self):
        import minerva.common
        assert hasattr(minerva.common, '__path__')

    def test_indexing_is_subpackage(self):
        import minerva.indexing
        assert hasattr(minerva.indexing, '__path__')

    def test_server_is_subpackage(self):
        import minerva.server
        assert hasattr(minerva.server, '__path__')


class TestImportErrors:
    def test_invalid_module_raises_import_error(self):
        with pytest.raises(ImportError):
            import minerva.nonexistent_module

    def test_invalid_submodule_raises_import_error(self):
        with pytest.raises(ImportError):
            from minerva.common import nonexistent

    def test_invalid_function_raises_attribute_error(self):
        from minerva.common import schemas
        with pytest.raises(AttributeError):
            schemas.nonexistent_function()


class TestDynamicImports:
    def test_dynamic_import_with_importlib(self):
        module = importlib.import_module('minerva.cli')
        assert hasattr(module, 'main')

    def test_dynamic_import_commands(self):
        commands = ['index', 'serve', 'peek', 'validate']
        for cmd in commands:
            module = importlib.import_module(f'minerva.commands.{cmd}')
            assert module is not None

    def test_dynamic_import_common_modules(self):
        common_modules = ['schemas', 'logger', 'config', 'ai_provider']
        for mod in common_modules:
            module = importlib.import_module(f'minerva.common.{mod}')
            assert module is not None

    def test_dynamic_import_indexing_modules(self):
        indexing_modules = ['chunking', 'embeddings', 'storage', 'json_loader']
        for mod in indexing_modules:
            module = importlib.import_module(f'minerva.indexing.{mod}')
            assert module is not None

    def test_dynamic_import_server_modules(self):
        server_modules = [
            'mcp_server',
            'search_tools',
            'collection_discovery',
            'context_retrieval',
            'startup_validation'
        ]
        for mod in server_modules:
            module = importlib.import_module(f'minerva.server.{mod}')
            assert module is not None


class TestFromImports:
    def test_from_cli_import_star(self):
        # Test that we can do from ... import *
        # Note: This is generally discouraged but should work
        namespace = {}
        exec('from minerva.cli import main, create_parser', namespace)
        assert 'main' in namespace
        assert 'create_parser' in namespace

    def test_from_common_schemas_import_multiple(self):
        from minerva.common.schemas import (
            validate_note,
            validate_notes_array,
            NOTE_SCHEMA
        )
        assert callable(validate_note)
        assert callable(validate_notes_array)
        assert isinstance(NOTE_SCHEMA, dict)

    def test_from_indexing_import_multiple(self):
        from minerva.indexing.chunking import create_chunks_from_notes
        from minerva.indexing.embeddings import generate_embeddings
        from minerva.indexing.storage import initialize_chromadb_client
        assert callable(create_chunks_from_notes)
        assert callable(generate_embeddings)
        assert callable(initialize_chromadb_client)
