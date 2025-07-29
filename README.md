# RStudio AI Assistant

R package for AI-powered assistance within RStudio.

## Features

- AI chat interface in RStudio Viewer
- Context-aware responses using RStudio environment
- PostgreSQL backend for data storage
- Automatic conversation management (10 max per user)
- PII-free architecture with access codes

## Installation

```r
devtools::install_github("NathanBresette/package_public")
```

## Usage

```r
library(rstudioai)
run_rgent()
```

## Deployment

- Backend: PostgreSQL database with automatic cleanup
- Frontend: RStudio Viewer integration
- Memory: Automatic conversation limits (10 max per user)

**Latest deployment: PostgreSQL migration complete - ready for redeploy!** 