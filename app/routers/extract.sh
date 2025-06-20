#!/bin/bash

# FastAPI Endpoint Extractor for Roomly App
# This script extracts all API endpoints from your FastAPI routers

# Set colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Output file
OUTPUT_FILE="roomly_api_endpoints.md"

echo -e "${GREEN}🔍 Extracting FastAPI endpoints from Roomly app...${NC}"

# Initialize output file
cat > "$OUTPUT_FILE" << 'EOF'
# Roomly API Endpoints

Generated on: $(date)

## Endpoint Summary

EOF

# Function to extract endpoints from Python files
extract_endpoints() {
    local file="$1"
    local router_name=$(basename "$file" .py)
    
    echo "### $router_name Router ($file)" >> "$OUTPUT_FILE"
    echo "" >> "$OUTPUT_FILE"
    
    # Extract router decorators and function definitions
    grep -n -A 5 -B 1 '@router\.\(get\|post\|put\|patch\|delete\)' "$file" | \
    while IFS= read -r line; do
        if [[ $line =~ ^[0-9]+-@router\.(get|post|put|patch|delete)\( ]]; then
            # Extract HTTP method and path
            method=$(echo "$line" | sed -n 's/.*@router\.\([^(]*\).*/\1/p')
            path=$(echo "$line" | sed -n 's/.*['\''\"]\([^'\''\"]*\)['\''\"]\(.*summary\|.*tags\|.*response_model\|.*status_code\|.*dependencies\|.*\)*/\1/p')
            
            if [ -n "$path" ]; then
                echo "| ${method^^} | \`$path\` | " >> "$OUTPUT_FILE"
            fi
        fi
    done
    
    echo "" >> "$OUTPUT_FILE"
}

# Function to extract route information with more details
extract_detailed_endpoints() {
    local file="$1"
    local router_name=$(basename "$file" .py)
    
    echo "#### Detailed $router_name Endpoints" >> "$OUTPUT_FILE"
    echo "" >> "$OUTPUT_FILE"
    
    # More comprehensive extraction
    python3 << EOF >> "$OUTPUT_FILE"
import re
import sys

try:
    with open('$file', 'r') as f:
        content = f.read()
    
    # Pattern to match FastAPI route decorators
    pattern = r'@router\.(get|post|put|patch|delete)\s*\(\s*["\']([^"\']+)["\'](?:[^)]*summary\s*=\s*["\']([^"\']+)["\'])?(?:[^)]*tags\s*=\s*\[([^\]]+)\])?[^)]*\)\s*\n(?:async\s+)?def\s+(\w+)'
    
    matches = re.finditer(pattern, content, re.MULTILINE | re.DOTALL)
    
    for match in matches:
        method = match.group(1).upper()
        path = match.group(2)
        summary = match.group(3) if match.group(3) else ""
        tags = match.group(4) if match.group(4) else ""
        func_name = match.group(5)
        
        print(f"**{method}** \`{path}\`")
        if summary:
            print(f"- Summary: {summary}")
        if tags:
            print(f"- Tags: {tags}")
        print(f"- Function: {func_name}")
        print("")

except Exception as e:
    print(f"Error processing $file: {e}")
    sys.exit(1)
EOF
}

# Main extraction logic
echo -e "${BLUE}📁 Searching for FastAPI router files...${NC}"

# Find all Python files that likely contain FastAPI routers
ROUTER_FILES=$(find . -name "*.py" -type f -exec grep -l "@router\.\(get\|post\|put\|patch\|delete\)" {} \; 2>/dev/null)

if [ -z "$ROUTER_FILES" ]; then
    echo -e "${RED}❌ No FastAPI router files found!${NC}"
    echo "Please ensure you're running this script from your FastAPI project root directory."
    exit 1
fi

echo -e "${GREEN}Found router files:${NC}"
echo "$ROUTER_FILES" | while read -r file; do
    echo -e "  📄 $file"
done

# Create summary table
echo "" >> "$OUTPUT_FILE"
echo "| Method | Endpoint | Router |" >> "$OUTPUT_FILE"
echo "|--------|----------|--------|" >> "$OUTPUT_FILE"

# Extract basic endpoint info for summary
echo "$ROUTER_FILES" | while read -r file; do
    if [ -f "$file" ]; then
        router_name=$(basename "$file" .py)
        
        # Extract endpoints with router info
        grep -n '@router\.\(get\|post\|put\|patch\|delete\)' "$file" | \
        while IFS= read -r line; do
            method=$(echo "$line" | sed -n 's/.*@router\.\([^(]*\).*/\1/p')
            path=$(echo "$line" | sed -n 's/.*['\''\"]\([^'\''\"]*\)['\''\"]\(.*summary\|.*tags\|.*response_model\|.*status_code\|.*dependencies\|.*\)*/\1/p')
            
            if [ -n "$path" ] && [ -n "$method" ]; then
                echo "| ${method^^} | \`$path\` | $router_name |" >> "$OUTPUT_FILE"
            fi
        done
    fi
done

# Add detailed sections
echo "" >> "$OUTPUT_FILE"
echo "## Detailed Endpoint Information" >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"

# Extract detailed info for each router
echo "$ROUTER_FILES" | while read -r file; do
    if [ -f "$file" ]; then
        echo -e "${YELLOW}🔍 Processing: $file${NC}"
        extract_detailed_endpoints "$file"
    fi
done

# Add file structure information
echo "" >> "$OUTPUT_FILE"
echo "## Project Structure" >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"
echo "\`\`\`" >> "$OUTPUT_FILE"
echo "FastAPI Router Files Found:" >> "$OUTPUT_FILE"
echo "$ROUTER_FILES" | while read -r file; do
    echo "$file" >> "$OUTPUT_FILE"
done
echo "\`\`\`" >> "$OUTPUT_FILE"

# Add route patterns analysis
echo "" >> "$OUTPUT_FILE"
echo "## Route Patterns Analysis" >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"

python3 << 'EOF' >> "$OUTPUT_FILE"
import re
import glob
import os

def analyze_routes():
    router_files = []
    
    # Find all Python files with FastAPI routes
    for root, dirs, files in os.walk('.'):
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, 'r') as f:
                        content = f.read()
                        if '@router.' in content and any(method in content for method in ['get', 'post', 'put', 'patch', 'delete']):
                            router_files.append(filepath)
                except:
                    continue
    
    # Extract all routes
    all_routes = []
    route_pattern = r'@router\.(get|post|put|patch|delete)\s*\(\s*["\']([^"\']+)["\']'
    
    for file in router_files:
        try:
            with open(file, 'r') as f:
                content = f.read()
                matches = re.finditer(route_pattern, content)
                for match in matches:
                    method = match.group(1).upper()
                    path = match.group(2)
                    router_name = os.path.basename(file).replace('.py', '')
                    all_routes.append((method, path, router_name, file))
        except:
            continue
    
    # Group by router
    routers = {}
    for method, path, router_name, file in all_routes:
        if router_name not in routers:
            routers[router_name] = []
        routers[router_name].append((method, path))
    
    # Print analysis
    print("### Routes by Router:")
    print()
    for router_name, routes in sorted(routers.items()):
        print(f"**{router_name}** ({len(routes)} endpoints)")
        for method, path in sorted(routes):
            print(f"- {method} `{path}`")
        print()
    
    # Print patterns
    print("### Common Route Patterns:")
    print()
    patterns = {}
    for method, path, router_name, file in all_routes:
        # Extract pattern (replace IDs with placeholder)
        pattern = re.sub(r'\{[^}]+\}', '{id}', path)
        if pattern not in patterns:
            patterns[pattern] = []
        patterns[pattern].append((method, router_name))
    
    for pattern, occurrences in sorted(patterns.items()):
        if len(occurrences) > 1:
            methods = [f"{method} ({router})" for method, router in occurrences]
            print(f"**`{pattern}`** - {', '.join(methods)}")
    
    print()
    print(f"**Total Endpoints:** {len(all_routes)}")
    print(f"**Total Routers:** {len(routers)}")

analyze_routes()
EOF

echo -e "${GREEN}✅ Endpoint extraction complete!${NC}"
echo -e "${BLUE}📝 Results saved to: $OUTPUT_FILE${NC}"
echo ""
echo -e "${YELLOW}📋 Quick Summary:${NC}"

# Show quick stats
TOTAL_ENDPOINTS=$(grep -c "^| [A-Z]" "$OUTPUT_FILE" 2>/dev/null || echo "0")
TOTAL_ROUTERS=$(echo "$ROUTER_FILES" | wc -l)

echo -e "  📊 Total Endpoints: $TOTAL_ENDPOINTS"
echo -e "  📁 Total Router Files: $TOTAL_ROUTERS"
echo ""
echo -e "${GREEN}🎉 You can now share the contents of '$OUTPUT_FILE' to get tailored React routing advice!${NC}"

# Optionally display the file
if command -v bat &> /dev/null; then
    echo -e "${BLUE}📖 Preview (using bat):${NC}"
    bat "$OUTPUT_FILE"
elif command -v cat &> /dev/null; then
    echo -e "${BLUE}📖 Preview:${NC}"
    cat "$OUTPUT_FILE"
fi