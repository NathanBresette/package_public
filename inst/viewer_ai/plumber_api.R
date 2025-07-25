# Plumber API for RStudio integration
# This provides local endpoints for the HTML interface to interact with RStudio

library(plumber)
library(rstudioapi)

#* @post /insert_code
#* @param code:string The code to insert into RStudio
function(code) {
  tryCatch({
    # Insert code into the active RStudio document
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