#* @get /
#* @serializer html
function() {
  static_dir <- system.file("public", package = "rstudioai")
  html_file <- file.path(static_dir, "index.html")
  if (file.exists(html_file)) {
    paste(readLines(html_file), collapse = "\n")
  } else {
    "<h1>HTML file not found</h1>"
  }
}

#* @get /context
function() {
  tryCatch({
    # Get document context if RStudio API is available
    document_content <- ""
    selection <- ""
    if (requireNamespace("rstudioapi", quietly = TRUE) && rstudioapi::isAvailable()) {
      tryCatch({
        ctx <- rstudioapi::getActiveDocumentContext()
        document_content <- paste(ctx$contents, collapse = "\n")
        selection <- if (length(ctx$selection) > 0) ctx$selection[[1]]$text else ""
      }, error = function(e) {
        document_content <- paste("Error getting document context:", e$message)
      })
    }
    
    # Get console history
    console_history <- tryCatch({
      history_file <- Sys.getenv("R_HISTFILE", file.path(Sys.getenv("HOME"), ".Rhistory"))
      if (file.exists(history_file)) {
        hist_lines <- readLines(history_file, n = 50)
        paste("Console History (last 50 lines):", paste(hist_lines, collapse = "\n"), sep = "\n")
      } else {
        "Console History: Not available"
      }
    }, error = function(e) "Console History: Error reading")
    
    # Get workspace objects with detailed info
    workspace_objects <- tryCatch({
      objects <- ls(envir = .GlobalEnv)
      if (length(objects) > 0) {
        obj_info <- sapply(objects, function(obj) {
          tryCatch({
            val <- get(obj, envir = .GlobalEnv)
            class_info <- paste(class(val), collapse = ", ")
            size_info <- if (is.data.frame(val)) paste(nrow(val), "rows,", ncol(val), "cols") else length(val)
            paste(obj, ":", class_info, "(", size_info, ")")
          }, error = function(e) paste(obj, ": Error getting info"))
        })
        paste("Workspace Objects:", paste(obj_info, collapse = "\n"), sep = "\n")
      } else {
        "Workspace Objects: None"
      }
    }, error = function(e) "Workspace Objects: Error reading")
    
    # Get environment information
    environment_info <- tryCatch({
      r_version <- paste("R Version:", R.version.string)
      platform <- paste("Platform:", R.version$platform)
      wd <- paste("Working Directory:", getwd())
      
      # Get loaded packages
      loaded_packages <- tryCatch({
        pkgs <- names(sessionInfo()$otherPkgs)
        if (length(pkgs) > 0) {
          pkg_versions <- sapply(pkgs, function(pkg) {
            tryCatch({
              version <- packageVersion(pkg)
              paste(pkg, "v", version)
            }, error = function(e) pkg)
          })
          paste("Loaded Packages:", paste(pkg_versions, collapse = ", "))
        } else {
          "Loaded Packages: None"
        }
      }, error = function(e) "Loaded Packages: Error reading")
      
      paste("Environment Info:", r_version, platform, wd, loaded_packages, sep = "\n")
    }, error = function(e) "Environment Info: Error reading")
    
    # Get custom functions (simplified)
    custom_functions <- tryCatch({
      objects <- ls(envir = .GlobalEnv)
      funcs <- objects[sapply(objects, function(obj) {
        tryCatch({
          val <- get(obj, envir = .GlobalEnv)
          is.function(val)
        }, error = function(e) FALSE)
      })]
      if (length(funcs) > 0) {
        paste("Custom Functions:", paste(funcs, collapse = ", "))
      } else {
        "Custom Functions: None"
      }
    }, error = function(e) "Custom Functions: Error reading")
    
    # Get plot history (simplified)
    plot_history <- tryCatch({
      plot_objects <- ls(envir = .GlobalEnv)[sapply(ls(envir = .GlobalEnv), function(obj) {
        tryCatch({
          val <- get(obj, envir = .GlobalEnv)
          inherits(val, c("ggplot", "trellis", "plot"))
        }, error = function(e) FALSE)
      })]
      if (length(plot_objects) > 0) {
        paste("Plot Objects:", paste(plot_objects, collapse = ", "))
      } else {
        "Plot Objects: None"
      }
    }, error = function(e) "Plot History: Error reading")
    
    # Get error history (simplified)
    error_history <- tryCatch({
      last_error <- ""
      if (exists(".Last.error", envir = .GlobalEnv)) {
        last_error <- paste("Last Error:", paste(capture.output(print(get(".Last.error", envir = .GlobalEnv))), collapse = "\n"))
      }
      if (last_error == "") {
        "Error History: None"
      } else {
        last_error
      }
    }, error = function(e) "Error History: Error reading")
    
    # Return context in the format expected by the backend
    list(
      document_content = document_content,
      selection = selection,
      console_history = console_history,
      workspace_objects = workspace_objects,
      environment_info = environment_info,
      custom_functions = custom_functions,
      plot_history = plot_history,
      error_history = error_history,
      timestamp = Sys.time(),
      source = "rstudio_plumber_context"
    )
  }, error = function(e) {
    list(
      error = paste("Error capturing context:", e$message),
      timestamp = Sys.time(),
      source = "rstudio_plumber_context"
    )
  })
}

#* @post /insert_code
function(req) {
  code <- req$body$code
  tryCatch({
    rstudioapi::insertText(code)
    list(success = TRUE, message = "Code inserted successfully")
  }, error = function(e) {
    list(success = FALSE, message = paste("Error inserting code:", e$message))
  })
}

#* @get /health
function() {
  list(status = "healthy", service = "rstudio-plumber-api")
}
