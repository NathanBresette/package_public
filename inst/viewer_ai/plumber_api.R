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
    # Get document content as a simple string
    document_content <- ""
    if (requireNamespace("rstudioapi", quietly = TRUE) && rstudioapi::isAvailable()) {
      tryCatch({
        ctx <- rstudioapi::getActiveDocumentContext()
        document_content <- paste(ctx$contents, collapse = "\n")
      }, error = function(e) {
        document_content <- paste("Error getting document context:", e$message)
      })
    }
    
    # Get console history as a simple string (temporarily simplified)
    console_history <- tryCatch({
      history_file <- Sys.getenv("R_HISTFILE", file.path(Sys.getenv("HOME"), ".Rhistory"))
      if (file.exists(history_file)) {
        paste(readLines(history_file, n = 10), collapse = "; ")
      } else {
        "Console History: Not available"
      }
    }, error = function(e) {
      "Console History: Error reading"
    })
    
    # Get workspace objects as a simple string (temporarily simplified)
    workspace_objects <- tryCatch({
      objects <- ls(envir = .GlobalEnv)
      if (length(objects) > 0) {
        obj_summaries <- sapply(objects, function(obj) {
          tryCatch({
            val <- get(obj, envir = .GlobalEnv)
            class_info <- paste(class(val), collapse = ", ")
            size_info <- if (is.data.frame(val)) paste(nrow(val), "rows,", ncol(val), "cols") else length(val)
            paste(obj, ":", class_info, "(", size_info, ")")
          }, error = function(e) paste(obj, ": Error getting info"))
        })
        paste(obj_summaries, collapse = "; ")
      } else {
        "No workspace objects"
      }
    }, error = function(e) {
      paste("Error reading workspace objects:", e$message)
    })
    
    # Get environment information as a simple string
    environment_info <- tryCatch({
      r_version <- paste("R Version:", R.version.string)
      platform <- paste("Platform:", R.version$platform)
      wd <- paste("Working Directory:", getwd())
      
      # Get loaded packages as a simple string
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
      }, error = function(e) paste("Loaded Packages: Error reading"))
      
      paste(r_version, platform, wd, loaded_packages, sep = "; ")
    }, error = function(e) {
      paste("Error reading environment info:", e$message)
    })
    
    # Get custom functions as a simple string
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
    }, error = function(e) {
      paste("Error reading functions:", e$message)
    })
    
    # Get plot history as a simple string
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
    }, error = function(e) {
      paste("Error reading plot history:", e$message)
    })
    
    # Get error history as a simple string
    error_history <- tryCatch({
      errors <- c()
      if (exists(".Last.error", envir = .GlobalEnv)) {
        last_error <- get(".Last.error", envir = .GlobalEnv)
        errors <- c(errors, paste("Last Error:", paste(capture.output(print(last_error)), collapse = " ")))
      }
      if (exists("last.warning", envir = .GlobalEnv)) {
        last_warnings <- get("last.warning", envir = .GlobalEnv)
        if (length(last_warnings) > 0) {
          errors <- c(errors, paste("Warnings:", paste(capture.output(print(last_warnings)), collapse = " ")))
        }
      }
      if (length(errors) == 0) {
        "No recent errors"
      } else {
        paste(errors, collapse = "; ")
      }
    }, error = function(e) {
      paste("Error reading error history:", e$message)
    })
    
    # Return context with all values as simple strings
    list(
      document_content = as.character(document_content),
      console_history = as.character(console_history),
      workspace_objects = as.character(workspace_objects),
      environment_info = as.character(environment_info),
      custom_functions = as.character(custom_functions),
      plot_history = as.character(plot_history),
      error_history = as.character(error_history),
      timestamp = as.character(Sys.time()),
      source = "rstudio_plumber_context"
    )
  }, error = function(e) {
    list(
      error = paste("Error capturing context:", e$message),
      timestamp = as.character(Sys.time()),
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
