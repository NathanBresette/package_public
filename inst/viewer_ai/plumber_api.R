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
    
    # Get console history as a simple list of strings
    console_history <- tryCatch({
      history_file <- Sys.getenv("R_HISTFILE", file.path(Sys.getenv("HOME"), ".Rhistory"))
      if (file.exists(history_file)) {
        as.list(readLines(history_file, n = 50))
      } else {
        list("Console History: Not available")
      }
    }, error = function(e) {
      list("Console History: Error reading")
    })
    
    # Get workspace objects as a simple dictionary with string values only
    workspace_objects <- tryCatch({
      objects <- ls(envir = .GlobalEnv)
      if (length(objects) > 0) {
        obj_dict <- list()
        for (obj in objects) {
          tryCatch({
            val <- get(obj, envir = .GlobalEnv)
            
            # Create simple object info with string values only
            obj_info <- list(
              type = if ("data.frame" %in% class(val)) "dataframe" else if (is.vector(val)) "vector" else if (is.list(val)) "list" else if (is.function(val)) "function" else "other",
              size = if (is.data.frame(val)) paste(nrow(val), "rows,", ncol(val), "cols") else as.character(length(val)),
              class = paste(class(val), collapse = ", ")
            )
            
            # Add simple type-specific details as strings only
            if (is.data.frame(val)) {
              obj_info$columns <- paste(colnames(val), collapse = ", ")
              obj_info$data_types <- paste(sapply(val, function(x) paste(class(x), collapse = ", ")), collapse = ", ")
            } else if (is.vector(val) && length(val) > 0) {
              obj_info$vector_type <- class(val)[1]
              obj_info$sample_values <- paste(as.character(head(val, 5)), collapse = ", ")
            } else if (is.list(val)) {
              obj_info$length <- as.character(length(val))
              obj_info$names <- paste(names(val), collapse = ", ")
            } else if (is.function(val)) {
              obj_info$arguments <- paste(names(formals(val)), collapse = ", ")
            }
            
            obj_dict[[obj]] <- obj_info
          }, error = function(e) {
            obj_dict[[obj]] <<- list(type = "error", size = "unknown", class = "error", error = e$message)
          })
        }
        obj_dict
      } else {
        list()
      }
    }, error = function(e) {
      list(error = paste("Error reading workspace objects:", e$message))
    })
    
    # Get environment information as a simple dictionary with string values
    environment_info <- tryCatch({
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
          paste(pkg_versions, collapse = ", ")
        } else {
          "No packages loaded"
        }
      }, error = function(e) {
        paste("Error reading packages:", e$message)
      })
      
      list(
        r_version = as.character(R.version.string),
        platform = as.character(R.version$platform),
        working_directory = as.character(getwd()),
        packages = loaded_packages
      )
    }, error = function(e) {
      list(error = paste("Error reading environment info:", e$message))
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
        paste(funcs, collapse = ", ")
      } else {
        "No custom functions"
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
        paste(plot_objects, collapse = ", ")
      } else {
        "No plot objects"
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
    
    # Return context in the format expected by the backend with string values only
    list(
      document_content = as.character(document_content),
      console_history = console_history,
      workspace_objects = workspace_objects,
      environment_info = environment_info,
      custom_functions = custom_functions,
      plot_history = plot_history,
      error_history = error_history,
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
