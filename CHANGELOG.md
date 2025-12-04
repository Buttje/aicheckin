# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed

- Commit messages now exclude LLM thinking process. Modern LLMs with 
  reasoning capabilities (e.g., DeepSeek, Qwen with thinking mode) 
  output their reasoning in tags like `<think>`, `<thinking>`, 
  `<thought>`, or `<reasoning>`. These tags and their contents are 
  now automatically filtered from commit messages, ensuring only the 
  final conclusion appears in the commit history.

## [0.1.0] - 2025-11-16

### Added

- Initial release of `aicheckin`, an AI‑powered commit assistant for
  Git and SVN. Features include automatic change detection,
  heuristic classification and grouping of commits, integration with
  an Ollama LLM for message generation, interactive acceptance or
  editing of proposed commits, non‑interactive mode for CI pipelines,
  comprehensive logging and defined exit codes.