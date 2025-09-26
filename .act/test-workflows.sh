#!/bin/bash
# Comprehensive workflow testing script

set -e

echo "🧪 Testing all workflows with nektos/act..."

# Test discover-releases workflow
echo ""
echo "📋 Testing discover-releases workflow..."
gh act workflow_dispatch -W .github/workflows/discover-releases.yml -e .act/payloads/workflow_dispatch_discover_releases.json --dryrun

# Test build-images workflow
echo ""
echo "🏗️ Testing build-images workflow..."
gh act workflow_dispatch -W .github/workflows/build-images.yml -e .act/payloads/workflow_dispatch_build_images.json --dryrun

# Test build-single-image workflow (dispatch)
echo ""
echo "🔨 Testing build-single-image workflow (dispatch)..."
gh act workflow_dispatch -W .github/workflows/build-single-image.yml -e .act/payloads/workflow_dispatch_build_single_image.json --dryrun

# Test push triggers
echo ""
echo "📤 Testing push triggers..."
gh act push -e .act/payloads/push_trigger.json --dryrun

# Validate all workflows
echo ""
echo "✅ Validating workflow syntax..."
gh act --validate

echo ""
echo "✅ All workflow tests completed successfully!"