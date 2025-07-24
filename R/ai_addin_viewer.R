#' Launch the AI assistant in the browser
#' One-command solution that opens the HTML interface connected to Render backend
#' @param port Port for the local plumber server (default: auto-detect)
#' @export
ai_addin_viewer <- function(port = NULL) {
  cat("Launching RStudio AI Assistant...\n")
  
  # 1. Install required packages if not already installed
  required_packages <- c("plumber", "callr", "httr", "jsonlite", "rstudioapi")
  missing_packages <- required_packages[!sapply(required_packages, requireNamespace, quietly = TRUE)]
  
  if (length(missing_packages) > 0) {
    cat("Installing required packages:", paste(missing_packages, collapse = ", "), "\n")
    utils::install.packages(missing_packages, repos = "https://cran.rstudio.com/")
    
    # Check if installation was successful
    still_missing <- missing_packages[!sapply(missing_packages, requireNamespace, quietly = TRUE)]
    if (length(still_missing) > 0) {
      cat("Failed to install packages:", paste(still_missing, collapse = ", "), "\n")
      return(invisible(FALSE))
    }
  }
  
  cat("All required packages are available\n")
  
  # 2. Start local plumber server for RStudio integration
  cat("Starting local plumber server for RStudio integration...\n")
  
  # Always find an available port if not specified
  if (is.null(port)) {
    tryCatch({
      port <- find_available_port()
      cat("Using dynamic port:", port, "\n")
    }, error = function(e) {
      cat("Could not find available port:", e$message, "\n")
      cat("Try specifying a port manually: ai_addin_viewer(port = 8889)\n")
      return(invisible(FALSE))
    })
  }
  # Ensure port is numeric and not NULL
  if (is.null(port) || !is.numeric(port) || is.na(port)) {
    cat("Invalid port. Please specify a valid port number.\n")
    return(invisible(FALSE))
  }
  
  # Start plumber server in background
  plumber_api_file <- file.path(system.file("viewer_ai", package = "rstudioai"), "plumber_api.R")
  
  if (file.exists(plumber_api_file)) {
    plumber_process <- callr::r_bg(function(api_file, server_port) {
      pr <- plumber::plumb(api_file)
      pr$run(host = "127.0.0.1", port = server_port)
    }, args = list(api_file = plumber_api_file, server_port = port))
    
    # Wait a moment for the server to start
    Sys.sleep(2)
    cat("Local plumber server started on port", port, "\n")
  } else {
    cat("Plumber API file not found\n")
    return(invisible(FALSE))
  }
  
  # 3. Test connection to Render backend
  cat("Testing connection to Render backend...\n")
  if (!test_backend_connection()) {
    cat("Cannot connect to Render backend. Please check your internet connection.\n")
    return(invisible(FALSE))
  }
  
  # 4. Open the HTML UI in browser
  cat("Opening AI Assistant in browser...\n")
  
  # Find the HTML file in the package
  html_file <- file.path(system.file("public", package = "rstudioai"), "index.html")
  
  if (file.exists(html_file)) {
    # Convert file path to URL with port parameter
    file_url <- paste0("file://", normalizePath(html_file), "?port=", port)
    cat("Opening URL:", file_url, "\n")
    
    # Try to open in browser
    tryCatch({
      if (Sys.info()["sysname"] == "Darwin") {
        system(paste("open", file_url))
      } else if (Sys.info()["sysname"] == "Linux") {
        system(paste("xdg-open", file_url))
      } else if (Sys.info()["sysname"] == "Windows") {
        system(paste("start", file_url))
      }
      cat("AI Assistant launched successfully!\n")
      cat("The AI assistant is now open in your browser.\n")
      cat("Use access code 'DEMO123' or 'TEST456' to validate access.\n")
      cat("AI responses come from Render backend, code insertion uses local plumber API.\n")
    }, error = function(e) {
      cat("Failed to open browser:", e$message, "\n")
      cat("Please manually open:", file_url, "\n")
    })
  } else {
    cat("HTML file not found:", html_file, "\n")
    return(invisible(FALSE))
  }
  
  invisible(TRUE)
} 