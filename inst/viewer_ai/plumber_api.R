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
    doc_context <- NULL
    if (requireNamespace("rstudioapi", quietly = TRUE) && rstudioapi::isAvailable()) {
      tryCatch({
        ctx <- rstudioapi::getActiveDocumentContext()
        doc_context <- list(
          document_content = paste(ctx$contents, collapse = "\n"),
          selection = if (length(ctx$selection) > 0) ctx$selection[[1]]$text else "",
          path = ctx$path,
          id = ctx$id
        )
      }, error = function(e) {
        doc_context <- list(error = paste("Error getting document context:", e$message))
      })
    }
    
    # Get workspace objects
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
    env_info <- tryCatch({
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
    
    # Return comprehensive context
    list(
      document_context = doc_context,
      workspace_objects = workspace_objects,
      environment_info = env_info,
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
