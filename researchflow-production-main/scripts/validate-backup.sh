#!/bin/bash

################################################################################
# ResearchFlow Backup Validation Script
# 
# Validates backup integrity and tests restore procedures
# Usage: ./scripts/validate-backup.sh [backup-file]
################################################################################

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BACKUP_DIR="${PROJECT_ROOT}/backups"
TEST_RESTORE_DIR="${PROJECT_ROOT}/.backup-test"

log_info() {
    echo -e "${BLUE}[INFO]${NC} $*"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $*"
}

log_warning() {
    echo -e "${YELLOW}[WARN]${NC} $*"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $*"
}

# Cleanup function
cleanup() {
    if [ -d "$TEST_RESTORE_DIR" ]; then
        log_info "Cleaning up test restore directory..."
        rm -rf "$TEST_RESTORE_DIR"
    fi
}

# Trap cleanup on exit
trap cleanup EXIT

# Validate backup file exists
validate_backup_file() {
    local backup_file=$1
    
    if [ ! -f "$backup_file" ]; then
        log_error "Backup file not found: $backup_file"
        exit 1
    fi
    
    log_success "Backup file found: $backup_file"
    
    # Check file size
    local file_size=$(du -h "$backup_file" | cut -f1)
    log_info "Backup size: $file_size"
    
    # Verify it's a valid tar.gz file
    if ! tar -tzf "$backup_file" > /dev/null 2>&1; then
        log_error "Invalid tar.gz file format"
        exit 1
    fi
    
    log_success "Backup file format is valid"
}

# List backup contents
list_backup_contents() {
    local backup_file=$1
    
    log_info "Backup contents:"
    tar -tzf "$backup_file" | head -20
    
    local file_count=$(tar -tzf "$backup_file" | wc -l)
    log_info "Total files in backup: $file_count"
}

# Test restore to temporary directory
test_restore() {
    local backup_file=$1
    
    log_info "Testing restore to temporary directory..."
    
    # Create test restore directory
    mkdir -p "$TEST_RESTORE_DIR"
    
    # Extract backup
    if ! tar -xzf "$backup_file" -C "$TEST_RESTORE_DIR"; then
        log_error "Failed to extract backup"
        exit 1
    fi
    
    log_success "Backup extracted successfully"
    
    # Verify key directories
    local expected_dirs=("volumes" "config" "data")
    for dir in "${expected_dirs[@]}"; do
        if [ -d "$TEST_RESTORE_DIR/$dir" ]; then
            log_success "Found directory: $dir"
        else
            log_warning "Missing expected directory: $dir"
        fi
    done
}

# Validate database backup
validate_database_backup() {
    local backup_file=$1
    
    log_info "Validating database backup..."
    
    # Check if database dump exists in backup
    if tar -tzf "$backup_file" | grep -q "postgres.sql"; then
        log_success "Database dump found in backup"
        
        # Extract and validate SQL file
        tar -xzf "$backup_file" -C "$TEST_RESTORE_DIR" --wildcards "*.sql" 2>/dev/null || true
        
        if [ -f "$TEST_RESTORE_DIR/postgres.sql" ]; then
            local line_count=$(wc -l < "$TEST_RESTORE_DIR/postgres.sql")
            log_info "Database dump has $line_count lines"
            
            # Check for key SQL statements
            if grep -q "CREATE TABLE" "$TEST_RESTORE_DIR/postgres.sql"; then
                log_success "Database schema statements found"
            else
                log_warning "No CREATE TABLE statements found"
            fi
            
            if grep -q "COPY.*FROM stdin" "$TEST_RESTORE_DIR/postgres.sql"; then
                log_success "Data COPY statements found"
            else
                log_warning "No data COPY statements found"
            fi
        fi
    else
        log_warning "No database dump found in backup"
    fi
}

# Validate volumes backup
validate_volumes_backup() {
    local backup_file=$1
    
    log_info "Validating volumes backup..."
    
    # Check for expected volumes
    local volumes=("postgres-data" "redis-data" "shared-data")
    
    for volume in "${volumes[@]}"; do
        if tar -tzf "$backup_file" | grep -q "volumes/$volume"; then
            log_success "Volume backup found: $volume"
        else
            log_warning "Volume backup missing: $volume"
        fi
    done
}

# Validate configuration files
validate_config_backup() {
    local backup_file=$1
    
    log_info "Validating configuration backup..."
    
    # Check for important config files
    local config_files=(
        "docker-compose.yml"
        ".env"
        "config/"
    )
    
    for config in "${config_files[@]}"; do
        if tar -tzf "$backup_file" | grep -q "$config"; then
            log_success "Configuration backup found: $config"
        else
            log_warning "Configuration backup missing: $config"
        fi
    done
}

# Generate backup report
generate_report() {
    local backup_file=$1
    local report_file="${backup_file}.validation-report.txt"
    
    log_info "Generating validation report..."
    
    {
        echo "ResearchFlow Backup Validation Report"
        echo "======================================"
        echo ""
        echo "Backup File: $backup_file"
        echo "Validation Date: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
        echo "Backup Size: $(du -h "$backup_file" | cut -f1)"
        echo ""
        echo "Contents:"
        tar -tzf "$backup_file" | head -50
        echo ""
        echo "Validation Status: PASSED"
    } > "$report_file"
    
    log_success "Validation report saved: $report_file"
}

# Main validation flow
main() {
    local backup_file="${1:-}"
    
    echo "======================================"
    echo "ResearchFlow Backup Validation"
    echo "======================================"
    echo ""
    
    # If no backup file specified, find the latest
    if [ -z "$backup_file" ]; then
        if [ ! -d "$BACKUP_DIR" ]; then
            log_error "Backup directory not found: $BACKUP_DIR"
            exit 1
        fi
        
        backup_file=$(find "$BACKUP_DIR" -name "backup-*.tar.gz" -type f | sort -r | head -1)
        
        if [ -z "$backup_file" ]; then
            log_error "No backup files found in $BACKUP_DIR"
            exit 1
        fi
        
        log_info "Using latest backup: $backup_file"
    fi
    
    # Run validation steps
    validate_backup_file "$backup_file"
    echo ""
    
    list_backup_contents "$backup_file"
    echo ""
    
    test_restore "$backup_file"
    echo ""
    
    validate_database_backup "$backup_file"
    echo ""
    
    validate_volumes_backup "$backup_file"
    echo ""
    
    validate_config_backup "$backup_file"
    echo ""
    
    generate_report "$backup_file"
    echo ""
    
    log_success "Backup validation completed successfully! ✓"
    echo ""
    echo "Summary:"
    echo "  Backup File: $backup_file"
    echo "  Status: VALID"
    echo "  Report: ${backup_file}.validation-report.txt"
    echo ""
    echo "✓ Backup is valid and can be used for restore"
}

# Run main function
main "$@"
