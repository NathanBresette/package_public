#' Launch the non-blocking AI assistant in the Viewer pane
#'
#' This function launches the RStudio AI Assistant in the Viewer pane. It automatically installs required packages, starts a background Plumber API, and opens a non-blocking HTML/JS UI for AI chat and code insertion.
#'
#' @param port Port for the Plumber API (default: NULL, will auto-select a free port)
#' @return The background Plumber process (invisible)
#' @examples
#' if (interactive()) ai_addin_viewer()
#' @export
ai_addin_viewer <- function(port = NULL) {
  cat("🚀 Setting up RStudio AI Assistant...\n")

  # 1. Install required packages if not already installed
  required_packages <- c("plumber", "callr", "httr", "jsonlite", "rstudioapi", "httpuv")
  missing_packages <- required_packages[!sapply(required_packages, requireNamespace, quietly = TRUE)]
  if (length(missing_packages) > 0) {
    cat("📦 Installing required packages:", paste(missing_packages, collapse = ", "), "\n")
    install.packages(missing_packages, repos = "https://cran.rstudio.com/")
    still_missing <- missing_packages[!sapply(missing_packages, requireNamespace, quietly = TRUE)]
    if (length(still_missing) > 0) {
      cat("❌ Failed to install packages:", paste(still_missing, collapse = ", "), "\n")
      return(invisible(FALSE))
    }
  }
  cat("✅ All required packages are available\n")

  # 2. Find a free port if not specified
  if (is.null(port)) {
    port <- httpuv::randomPort()
  }
  cat("🔌 Using Plumber API port:", port, "\n")

  # 3. Get viewer_ai resource path from package
  viewer_ai_path <- system.file("viewer_ai", package = "rstudioai")
  if (!dir.exists(viewer_ai_path)) {
    cat("❌ viewer_ai directory not found in package resources.\n")
    return(invisible(FALSE))
  }

  # 4. Start Plumber API in background
  cat("🔌 Starting Plumber API on port", port, "...\n")
  # Start new Plumber process
  plumber_process <- callr::r_bg(function(port, viewer_ai_path) {
    library(plumber)
    library(rstudioapi)
    library(jsonlite)
    plumber_file <- file.path(viewer_ai_path, "plumber_bridge.R")
    if (file.exists(plumber_file)) {
      pr <- plumber::plumb(plumber_file)
      pr$run(port = port, host = "127.0.0.1")
    } else {
      stop("Plumber bridge file not found")
    }
  }, args = list(port = port, viewer_ai_path = viewer_ai_path))
  Sys.sleep(2)

  # 5. Capture environment context (but don't send separately)
  cat("📊 Capturing environment context...\n")
  tryCatch({
    source(file.path(viewer_ai_path, "context_capture.R"))
    context_data <- send_env_context_to_backend()
    cat("✅ Environment context captured (will be sent with chat requests)\n")
  }, error = function(e) {
    cat("⚠️  Warning: Could not capture environment context:", e$message, "\n")
  })

  # 6. Inject dynamic port into HTML and open in Viewer
  cat("🌐 Opening AI Assistant in Viewer pane...\n")
  html_file <- file.path(viewer_ai_path, "index.html")
  if (file.exists(html_file)) {
    html_lines <- readLines(html_file)
    # Replace the plumberUrl line with the dynamic port
    html_lines <- gsub(
      'const plumberUrl = ".*";',
      sprintf('const plumberUrl = "http://127.0.0.1:%d/insert_code";', port),
      html_lines
    )
    tmp_html <- tempfile(fileext = ".html")
    writeLines(html_lines, tmp_html)
    rstudioapi::viewer(tmp_html)
    cat("✅ AI Assistant launched successfully!\n")
    cat("💡 You can now use the AI assistant while running other R code.\n")
  } else {
    cat("❌ HTML file not found:", html_file, "\n")
    return(invisible(FALSE))
  }

  invisible(plumber_process)
} 