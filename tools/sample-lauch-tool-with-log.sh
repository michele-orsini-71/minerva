#!/bin/sh
minerva index --config "Bear Notes 2025-10-26 at 11.11-config.json" --verbose 2>&1 | ts '[%Y-%m-%d %H:%M:%.S]' | tee indexing.log