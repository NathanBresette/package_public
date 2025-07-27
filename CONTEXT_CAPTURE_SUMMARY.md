# Context Capture Summary

## Access Codes Available for Testing

### Test Access Code
- **Access Code**: `TEST123`
- **Status**: ✅ Active and working
- **Daily Limit**: 1000 requests
- **Monthly Budget**: $100.0
- **Created**: Via admin API

### Demo Access Code (if available)
- **Access Code**: `DEMO123`
- **Status**: May need to be created in database

## Context Data Structure Captured

The package captures the following context data when you use the RStudio add-in:

### 1. Document Content
- **Source**: Active RStudio document
- **Content**: Current code in the editor
- **Example**: 
```r
data <- read.csv("sample_data.csv")
summary(data)
plot(data$x, data$y)
```

### 2. Console History
- **Source**: R console history file
- **Content**: Recent console commands (last 20)
- **Example**:
```r
c("library(ggplot2)", "data <- mtcars", "head(data)", "summary(data)")
```

### 3. Workspace Objects
- **Source**: Objects in global environment
- **Structure**: List with object metadata
- **Example**:
```r
list(
  mtcars = list(
    class = "data.frame",
    rows = 32,
    columns = 11,
    preview = "Mazda RX4: 21.0 6 160 110 3.90 2.620 16.46 0 1 4 4"
  ),
  iris = list(
    class = "data.frame", 
    rows = 150,
    columns = 5,
    preview = "Sepal.Length Sepal.Width Petal.Length Petal.Width Species"
  )
)
```

### 4. Environment Information
- **Source**: R session info
- **Content**: R version, platform, working directory, loaded packages
- **Example**:
```r
list(
  r_version = "R version 4.5.1",
  platform = "x86_64-apple-darwin20", 
  working_directory = "/Users/nathanbresette/rstudioai",
  packages = "ggplot2, dplyr, httr, jsonlite"
)
```

### 5. Custom Functions
- **Source**: User-defined functions in workspace
- **Content**: Function names and definitions
- **Example**:
```r
c("my_plot <- function(x, y) { plot(x, y, main=\"Custom Plot\") }")
```

### 6. Plot History
- **Source**: Recent plot commands
- **Content**: Plot commands executed
- **Example**:
```r
c("hist(mtcars$mpg)", "boxplot(iris$Sepal.Length ~ iris$Species)")
```

### 7. Error History
- **Source**: Recent error messages
- **Content**: Error messages from console
- **Example**:
```r
c("Error in read.csv(\"missing_file.csv\"): cannot open file")
```

### 8. Metadata
- **Timestamp**: When context was captured
- **Source**: Source of context (e.g., "rstudio_addin")

## How to Test Context Capture

### Step 1: Install and Load Package
```r
devtools::install_github("NathanBresette/rgent-ai")
library(rstudioai)
```

### Step 2: Create Test Data in RStudio
```r
# Create some test data
mtcars_test <- mtcars[1:5, 1:3]
iris_test <- iris[1:3, ]
my_function <- function(x) { x * 2 }

# Create some plots
hist(mtcars$mpg)
boxplot(iris$Sepal.Length ~ iris$Species)

# Try some commands
library(ggplot2)
head(mtcars)
summary(iris)
```

### Step 3: Run the Add-in
```r
ai_addin_viewer()
```

### Step 4: Enter Access Code
- Use `TEST123` as the access code
- The system will capture all the context data above

### Step 5: Check Captured Data
Run the analysis script:
```r
source("check_context_capture.R")
```

## Backend Endpoints for Context

### Validation
- **Endpoint**: `POST /validate`
- **Purpose**: Validate access code
- **Test**: `TEST123` ✅ Working

### Chat with Context
- **Endpoint**: `POST /chat`
- **Purpose**: Send chat request with context
- **Context Structure**: As described above

### Usage Tracking
- **Endpoint**: `GET /usage/{access_code}`
- **Purpose**: Track usage statistics

### Context Summary
- **Endpoint**: `GET /context/summary/{access_code}`
- **Purpose**: Get stored context summary

### Conversations
- **Endpoint**: `GET /conversations/{access_code}`
- **Purpose**: Get conversation history

## Testing Instructions

1. **Open RStudio**
2. **Install package**: `devtools::install_github("NathanBresette/rgent-ai")`
3. **Load package**: `library(rstudioai)`
4. **Create test data** (see examples above)
5. **Run add-in**: `ai_addin_viewer()`
6. **Enter access code**: `TEST123`
7. **Test chat functionality**
8. **Run analysis script**: `source("check_context_capture.R")`

## Expected Context Capture

When you test with `TEST123`, the system should capture:

- ✅ **Document content** from active RStudio document
- ✅ **Console history** from recent commands
- ✅ **Workspace objects** with metadata (class, rows, columns, preview)
- ✅ **Environment info** (R version, platform, packages)
- ✅ **Custom functions** defined in workspace
- ✅ **Plot history** from recent plot commands
- ✅ **Error history** from console errors
- ✅ **Timestamp** and source information

The context data is then sent to the backend for AI processing and stored for future reference. 