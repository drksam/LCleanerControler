# GitHub Version Management & Branching Strategy

This document outlines the recommended approach for managing versions and preserving stable code when pushing new features to GitHub.

## Overview

When developing new features, it's crucial to preserve working versions while allowing for experimental development. This guide covers the strategies implemented for the LCleaner Controller project.

## Strategy Used: Release Tags + Feature Branches

### Why This Approach?
- **Preserves stable versions** through release tags
- **Allows safe development** in feature branches  
- **Enables easy rollback** to any previous version
- **Maintains clean main branch** for production use

## Implementation Steps

### Step 1: Create a Stable Release Tag

Before adding untested features, tag the current working version:

```bash
# Create an annotated tag for the current stable version
git tag -a v2.0.2-stable -m "Stable version before table limit switches and go-to-zero features - most functionality tested and working"

# Push the tag to GitHub to preserve it
git push origin v2.0.2-stable
```

**Result**: This creates a permanent snapshot of your working code that you can always return to.

### Step 2: Create a Feature Branch

Create a dedicated branch for new untested features:

```bash
# Create and switch to a new feature branch
git checkout -b feature/table-limit-switches-go-to-zero
```

**Result**: You're now working in an isolated environment where you can safely develop new features.

### Step 3: Commit and Push New Features

Add your changes to the feature branch:

```bash
# Stage all changes
git add .

# Commit with detailed message
git commit -m "Add table limit switch controls and cleaning head go-to-zero functionality

Features added:
- Table run to front/back limit switch controls with safety checking
- Cleaning head GO to zero positioning at index speed  
- Backend API routes: /table/run_to_front_limit, /table/run_to_back_limit, /go_to_zero
- Frontend buttons on table, cleaning head, and operation pages
- Full sequence automation integration for all new step types
- Comprehensive error handling and simulation mode support

Status: UNTESTED - Requires physical hardware verification"

# Push the feature branch to GitHub
git push -u origin feature/table-limit-switches-go-to-zero
```

**Result**: Your new features are safely stored in GitHub without affecting the stable main branch.

## Branch Management Options

### Option A: Test and Merge (Recommended)
1. Test the new features on physical hardware (Raspberry Pi)
2. If everything works: Create a Pull Request to merge into main
3. If issues found: Fix them in the feature branch, then merge

### Option B: Continue Development
- Keep developing in the feature branch
- Main branch stays stable for production use
- Switch between branches as needed:
  ```bash
  git checkout main                                    # Switch to stable version
  git checkout feature/table-limit-switches-go-to-zero # Switch to new features
  ```

### Option C: Emergency Rollback
If you need to quickly revert to the stable version:
```bash
git checkout main
git reset --hard v2.0.2-stable
```

## Current Project State

### Stable Version (v2.0.2-stable tag)
- **Status**: Tested and working
- **Location**: Available via tag `v2.0.2-stable`
- **Access**: `git checkout v2.0.2-stable`

### Development Version (feature branch)
- **Branch**: `feature/table-limit-switches-go-to-zero`
- **Status**: Implementation complete, untested on hardware
- **Features Added**:
  - Table run to front/back limit switch controls
  - Cleaning head GO to zero functionality
  - Complete sequence automation integration
  - Comprehensive error handling and simulation support

## Best Practices for Future Development

### 1. Always Tag Stable Releases
Before major changes, create a release tag:
```bash
git tag -a v2.0.3-stable -m "Description of stable state"
git push origin v2.0.3-stable
```

### 2. Use Feature Branches
For each new feature or major change:
```bash
git checkout -b feature/descriptive-name
# Develop, commit, push
git push -u origin feature/descriptive-name
```

### 3. Keep Main Branch Stable
- Only merge tested, working features into main
- Use Pull Requests for code review
- Test thoroughly before merging

### 4. Regular Cleanup
After merging feature branches:
```bash
# Delete local branch
git branch -d feature/old-feature-name

# Delete remote branch
git push origin --delete feature/old-feature-name
```

## Git Command Quick Reference

### Branch Operations
```bash
# List all branches
git branch -a

# Create new branch
git checkout -b feature/new-feature

# Switch branches
git checkout main
git checkout feature/existing-feature

# Delete branch
git branch -d feature/old-feature
```

### Tag Operations
```bash
# List all tags
git tag -l

# Create annotated tag
git tag -a v1.0.0 -m "Version 1.0.0"

# Push tag to remote
git push origin v1.0.0

# Checkout specific tag
git checkout v1.0.0
```

### Remote Operations
```bash
# Push new branch
git push -u origin feature/new-feature

# Push tags
git push origin --tags

# Fetch all branches and tags
git fetch --all --tags
```

## Recovery Scenarios

### Scenario 1: Need to Rollback Everything
```bash
git checkout main
git reset --hard v2.0.2-stable
git push --force origin main  # Use with caution!
```

### Scenario 2: Feature Branch Has Issues
```bash
# Switch to main and create new branch
git checkout main
git checkout -b feature/fixed-version

# Or reset feature branch to stable
git checkout feature/problematic-branch
git reset --hard v2.0.2-stable
```

### Scenario 3: Merge Feature After Testing
```bash
# Switch to main
git checkout main

# Merge feature branch
git merge feature/table-limit-switches-go-to-zero

# Push to remote
git push origin main

# Tag new stable version
git tag -a v2.0.3-stable -m "Stable with table limit switches and go-to-zero"
git push origin v2.0.3-stable
```

## Conclusion

This branching strategy provides:
- ✅ **Safety**: Stable versions are always preserved
- ✅ **Flexibility**: Easy to switch between stable and development versions
- ✅ **Organization**: Clear separation between tested and untested code
- ✅ **Collaboration**: Feature branches enable safe collaborative development
- ✅ **Recovery**: Multiple rollback options available

The key is to always tag stable versions before making major changes and use feature branches for all new development work.