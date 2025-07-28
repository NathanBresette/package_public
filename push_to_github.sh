#!/bin/bash

# Script to push the clean R package to GitHub

echo "🚀 Preparing to push clean R package to GitHub..."

# Navigate to the clean package directory
cd clean_rstudioai

# Initialize git repository (if not already done)
if [ ! -d ".git" ]; then
    echo "📁 Initializing git repository..."
    git init
fi

# Add all files
echo "📦 Adding files to git..."
git add .

# Commit changes
echo "💾 Committing changes..."
git commit -m "Initial commit: Clean RStudio AI Assistant package"

# Add remote origin (replace with your actual GitHub repo URL)
echo "🔗 Adding remote origin..."
git remote add origin https://github.com/NathanBresette/Rgent-AI.git

# Push to GitHub
echo "⬆️ Pushing to GitHub..."
git push -u origin main

echo "✅ Package pushed to GitHub successfully!"
echo "📋 Users can now install with: devtools::install_github('NathanBresette/Rgent-AI', force = TRUE)" 