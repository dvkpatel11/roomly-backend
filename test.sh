#!/bin/bash

# Script to find unused class declarations in a FastAPI project
# Usage: ./find_unused_classes.sh [directory]

# Set the directory to search (default to current directory)
SEARCH_DIR="${1:-.}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Searching for unused classes in: $SEARCH_DIR${NC}"
echo "----------------------------------------"

# Find all Python files, excluding common directories to ignore
python_files=$(find "$SEARCH_DIR" -name "*.py" -type f \
    -not -path "*/__pycache__/*" \
    -not -path "*/.venv/*" \
    -not -path "*/venv/*" \
    -not -path "*/env/*" \
    -not -path "*/.env/*" \
    -not -path "*/node_modules/*" \
    -not -path "*/.git/*" \
    -not -path "*/migrations/*" \
    -not -path "*/alembic/versions/*" \
    -not -path "*/.pytest_cache/*" \
    -not -path "*/.mypy_cache/*" \
    -not -path "*/site-packages/*" \
    -not -path "*/.tox/*" \
    -not -path "*/build/*" \
    -not -path "*/dist/*")

# Array to store unused classes
declare -a unused_classes

# Function to extract class names from a file
extract_classes() {
    local file="$1"
    # Extract class declarations (handles inheritance and multiple bases) - exact match
    grep -nE "^class [A-Za-z_][A-Za-z0-9_]*\b" "$file" | sed -E 's/^([0-9]+):.*class ([A-Za-z_][A-Za-z0-9_]*).*/\1:\2/'
}

# Function to find where a class is used
find_class_usage() {
    local class_name="$1"
    local defining_file="$2"
    
    # Search patterns for class usage - using word boundaries for exact matches
    local patterns=(
        # Direct instantiation - exact match with word boundary
        "\b$class_name("
        # Inheritance - exact match in class definition
        "class [^(]*\($class_name\b"
        "class [^(]*\([^)]*,\s*$class_name\b"
        "class [^(]*\b$class_name\s*,"
        "class [^(]*\b$class_name\s*\)"
        # Type hints - exact match with word boundaries
        ":\s*$class_name\b"
        "->\s*$class_name\b"
        # Generic types - exact match
        "\[$class_name\]"
        "List\[$class_name\]"
        "Optional\[$class_name\]"
        "Union\[[^]]*\b$class_name\b"
        "Dict\[[^]]*\b$class_name\b"
        "Tuple\[[^]]*\b$class_name\b"
        # Import statements - exact match
        "from [^ ]* import [^#]*\b$class_name\b"
        "import [^#]*\b$class_name\b"
        # Runtime type checking - exact match
        "isinstance\([^,]*,\s*$class_name\b"
        "issubclass\([^,]*,\s*$class_name\b"
        # FastAPI specific patterns - exact match
        "Depends\($class_name\b"
        "response_model\s*=\s*$class_name\b"
        # Decorators - exact match
        "@$class_name\b"
        # Variable assignment - exact match
        "=\s*$class_name\b"
        "=\s*$class_name("
    )
    
    # Temporary file to store usage locations
    local temp_file=$(mktemp)
    
    # Check all Python files except the defining file for usage
    for file in $python_files; do
        if [[ "$file" != "$defining_file" ]]; then
            for pattern in "${patterns[@]}"; do
                # Use grep -E for extended regex and -w flag won't work with our complex patterns
                grep -nE "$pattern" "$file" 2>/dev/null | while IFS=: read -r line_num line_content; do
                    if [[ -n "$line_num" && -n "$line_content" ]]; then
                        # Additional validation: skip comments and string literals where possible
                        # Skip obvious comment lines
                        if [[ ! "$line_content" =~ ^[[:space:]]*# ]]; then
                            echo "$file:$line_num:$line_content" >> "$temp_file"
                        fi
                    fi
                done
            done
        fi
    done
    
    # Also check within the same file (but not the declaration line)
    local defining_line=$(grep -n "^class $class_name\b" "$defining_file" | cut -d: -f1)
    for pattern in "${patterns[@]}"; do
        grep -nE "$pattern" "$defining_file" 2>/dev/null | grep -v "^$defining_line:" | while IFS=: read -r line_num line_content; do
            if [[ -n "$line_num" && -n "$line_content" ]]; then
                # Skip obvious comment lines
                if [[ ! "$line_content" =~ ^[[:space:]]*# ]]; then
                    echo "$defining_file:$line_num:$line_content" >> "$temp_file"
                fi
            fi
        done
    done
    
    # Read the results and clean up
    if [[ -s "$temp_file" ]]; then
        cat "$temp_file"
    fi
    rm -f "$temp_file"
}

# Function to check if a class is used (simplified version)
is_class_used() {
    local class_name="$1"
    local defining_file="$2"
    
    local usage_output=$(find_class_usage "$class_name" "$defining_file")
    [[ -n "$usage_output" ]]
}

# Main logic
total_classes=0
unused_count=0

for file in $python_files; do
    echo -e "${YELLOW}Checking: $file${NC}"
    
    # Get all classes in this file
    classes_info=$(extract_classes "$file")
    
    if [[ -n "$classes_info" ]]; then
        while IFS= read -r class_info; do
            if [[ -n "$class_info" ]]; then
                line_num=$(echo "$class_info" | cut -d: -f1)
                class_name=$(echo "$class_info" | cut -d: -f2)
                
                total_classes=$((total_classes + 1))
                
                echo "  Found class: $class_name (line $line_num)"
                
                # Get usage locations for this class
                usage_output=$(find_class_usage "$class_name" "$file")
                
                if [[ -z "$usage_output" ]]; then
                    echo -e "    ${RED}⚠️  UNUSED: $class_name in $file:$line_num${NC}"
                    unused_classes+=("$file:$line_num:$class_name")
                    unused_count=$((unused_count + 1))
                else
                    # Count usage locations
                    usage_count=$(echo "$usage_output" | wc -l)
                    echo -e "    ${GREEN}✓ Used in $usage_count location(s)${NC}"
                    
                    # Show first few usage locations
                    show_count=3
                    count=0
                    while IFS= read -r usage_line; do
                        if [[ $count -ge $show_count ]]; then
                            remaining=$((usage_count - show_count))
                            if [[ $remaining -gt 0 ]]; then
                                echo -e "      ${GREEN}... and $remaining more${NC}"
                            fi
                            break
                        fi
                        if [[ -n "$usage_line" ]]; then
                            usage_file=$(echo "$usage_line" | cut -d: -f1)
                            usage_line_num=$(echo "$usage_line" | cut -d: -f2)
                            usage_content=$(echo "$usage_line" | cut -d: -f3- | sed 's/^[[:space:]]*//' | cut -c1-80)
                            echo -e "      ${GREEN}→${NC} $usage_file:$usage_line_num ${GREEN}$usage_content${NC}"
                            count=$((count + 1))
                        fi
                    done <<< "$usage_output"
                fi
            fi
        done <<< "$classes_info"
    fi
    echo
done

# Summary
echo "========================================"
echo -e "${GREEN}SUMMARY${NC}"
echo "========================================"
echo "Total classes found: $total_classes"
echo -e "Unused classes: ${RED}$unused_count${NC}"

if [[ $unused_count -gt 0 ]]; then
    echo
    echo -e "${RED}UNUSED CLASSES:${NC}"
    echo "----------------"
    for unused in "${unused_classes[@]}"; do
        IFS=':' read -r file line class <<< "$unused"
        echo -e "${RED}• $class${NC} in ${YELLOW}$file${NC} (line $line)"
    done
    
    echo
    echo -e "${YELLOW}NOTE: This script uses pattern matching and may have false positives.${NC}"
    echo -e "${YELLOW}Please manually verify before removing any classes.${NC}"
    echo -e "${YELLOW}Some classes might be used dynamically or in ways not detected by this script.${NC}"
fi

echo
echo "Done!"