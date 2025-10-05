import sys

import pytest

import args_parser


def test_parse_pipeline_args_success(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(sys, "argv", ["prog", "--config", "config.json", "--dry-run", "-v"])
    args = args_parser.parse_pipeline_args()
    assert args.config == "config.json"
    assert args.dry_run is True
    assert args.verbose is True


def test_parse_pipeline_args_missing_config(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(sys, "argv", ["prog"])
    with pytest.raises(SystemExit):
        args_parser.parse_pipeline_args()
