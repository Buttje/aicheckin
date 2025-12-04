# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed

- Enhanced commit message generation to filter out LLM thinking process and meta-commentary
- Updated prompt to explicitly instruct LLM to output only the final commit message
- Improved message normalization to handle cases where LLM suggests different commit types

### Added

- New `_extract_commit_message` method to remove thinking process from LLM responses
- Comprehensive tests for commit message extraction with various LLM response patterns

## [0.1.0] - 2025-11-16

### Added

- Initial release of `aicheckin`, an AI‑powered commit assistant for
  Git and SVN. Features include automatic change detection,
  heuristic classification and grouping of commits, integration with
  an Ollama LLM for message generation, interactive acceptance or
  editing of proposed commits, non‑interactive mode for CI pipelines,
  comprehensive logging and defined exit codes.