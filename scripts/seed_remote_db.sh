#!/bin/bash
# =============================================================================
# Remote Database Seeding Script for Cloud Run Environments
# =============================================================================
#
# Seeds deployed Cloud Run environments by downloading the SQLite database
# from GCS, seeding it locally, and uploading it back.
#
# USAGE:
#   ./scripts/seed_remote_db.sh <environment> [seed_flags...]
#
# EXAMPLES:
#   ./scripts/seed_remote_db.sh dev --demo --clear
#   ./scripts/seed_remote_db.sh staging --demo --clear
#
# ENVIRONMENTS:
#   dev      - dev.loopcloser.io (loopcloser-db-dev)
#   staging  - staging.loopcloser.io (loopcloser-db-staging)
#   prod     - loopcloser.io (loopcloser-db-prod) [USE WITH CAUTION]
#
# =============================================================================

set -e  # Exit on error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ID="loopcloser"
REGION="us-central1"

# =============================================================================
# Helper Functions
# =============================================================================

log_info() {
    echo -e "${BLUE}ℹ${NC}  $1"
}

log_success() {
    echo -e "${GREEN}✓${NC}  $1"
}

log_warning() {
    echo -e "${YELLOW}⚠${NC}  $1"
}

log_error() {
    echo -e "${RED}✗${NC}  $1"
}

print_usage() {
    cat << EOF
Usage: $0 <environment> [seed_flags...]

Environments:
  dev      - Seed dev.loopcloser.io database
  staging  - Seed staging.loopcloser.io database
  prod     - Seed production database (DANGEROUS - use with extreme caution)

Seed Flags (passed to seed_db.py):
  --demo   - Seed full demo dataset
  --clear  - Clear database before seeding
  --manifest <path> - Use custom manifest file

Examples:
  $0 dev --demo --clear
  $0 staging --demo --clear
  $0 dev --manifest demos/custom_demo.json

EOF
}

check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check gcloud CLI
    if ! command -v gcloud &> /dev/null; then
        log_error "gcloud CLI not found. Install from: https://cloud.google.com/sdk/docs/install"
        exit 1
    fi
    
    # Check gsutil
    if ! command -v gsutil &> /dev/null; then
        log_error "gsutil not found. Should come with gcloud CLI."
        exit 1
    fi
    
    # Check authentication
    if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" &> /dev/null; then
        log_error "Not authenticated with gcloud. Run: gcloud auth login"
        exit 1
    fi
    
    # Check project access
    CURRENT_PROJECT=$(gcloud config get-value project 2>/dev/null || echo "")
    if [ "$CURRENT_PROJECT" != "$PROJECT_ID" ]; then
        log_warning "Current project is '$CURRENT_PROJECT', expected '$PROJECT_ID'"
        log_info "Setting project to $PROJECT_ID..."
        gcloud config set project "$PROJECT_ID"
    fi
    
    log_success "Prerequisites validated"
}

confirm_action() {
    local env=$1
    local service_name=$2
    local seed_flags="${@:3}"
    
    # Check if --clear flag is present
    local is_destructive=false
    if [[ " $seed_flags " =~ " --clear " ]]; then
        is_destructive=true
    fi
    
    echo ""
    echo "╔════════════════════════════════════════════════════════════╗"
    if [ "$is_destructive" = true ]; then
        log_error "║  ⚠️  DESTRUCTIVE OPERATION - DATABASE WILL BE WIPED  ⚠️   ║"
    else
        log_warning "║         DATABASE SEEDING CONFIRMATION REQUIRED          ║"
    fi
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""
    
    if [ "$is_destructive" = true ]; then
        log_error "THIS WILL PERMANENTLY DELETE ALL DATA in the ${env} environment!"
        log_error "Database: gs://loopcloser-db-${env}/loopcloser.db"
        log_error "Service: ${service_name} at https://${env}.loopcloser.io"
    else
        log_warning "You are about to seed the ${env} environment database"
        log_warning "Service: ${service_name} at https://${env}.loopcloser.io"
    fi
    
    echo ""
    log_info "This operation will:"
    echo "  1. Create a backup in gs://loopcloser-db-${env}/backups/"
    echo "  2. Scale down the Cloud Run service (brief downtime)"
    echo "  3. Download the database from GCS"
    if [ "$is_destructive" = true ]; then
        echo "  4. CLEAR ALL DATA and seed with fresh dataset"
    else
        echo "  4. Seed the database (may modify existing data)"
    fi
    echo "  5. Upload the modified database back to GCS"
    echo "  6. Restore the Cloud Run service"
    echo ""
    
    if [ "$env" == "prod" ]; then
        log_error "════════════════════════════════════════════════════════════"
        log_error "⚠️⚠️⚠️  PRODUCTION ENVIRONMENT - EXTREME CAUTION  ⚠️⚠️⚠️"
        log_error "════════════════════════════════════════════════════════════"
        echo ""
    fi
    
    # Require typing the environment name to confirm
    echo ""
    log_warning "To proceed, type the environment name exactly: ${env}"
    echo -ne "${YELLOW}Type '${env}' to confirm: ${NC}"
    read confirmation
    
    if [ "$confirmation" != "$env" ]; then
        echo ""
        log_error "Confirmation failed. Expected '${env}', got '${confirmation}'"
        log_info "Operation aborted - no changes made"
        exit 0
    fi
    
    echo ""
    log_success "Confirmation received. Proceeding with database seeding..."
}

create_backup() {
    local bucket=$1
    local timestamp=$(date +%Y%m%d-%H%M%S)
    local backup_path="backups/loopcloser-${timestamp}.db"
    
    log_info "Creating backup: gs://${bucket}/${backup_path}"
    
    if gsutil -q stat "gs://${bucket}/loopcloser.db" 2>/dev/null; then
        gsutil cp "gs://${bucket}/loopcloser.db" "gs://${bucket}/${backup_path}"
        log_success "Backup created"
    else
        log_warning "No existing database found to backup (this may be first deployment)"
    fi
}

scale_service() {
    local service_name=$1
    local min_instances=$2
    local max_instances=$3
    
    log_info "Scaling service to min=${min_instances}, max=${max_instances}..."
    
    gcloud run services update "$service_name" \
        --region="$REGION" \
        --min-instances="$min_instances" \
        --max-instances="$max_instances" \
        --quiet
    
    # Wait a moment for scaling to take effect
    sleep 3
    
    log_success "Service scaled"
}

download_database() {
    local bucket=$1
    local local_db=$2
    
    log_info "Downloading database from gs://${bucket}/loopcloser.db..."
    
    # Download or create empty file if doesn't exist
    if gsutil -q stat "gs://${bucket}/loopcloser.db" 2>/dev/null; then
        gsutil cp "gs://${bucket}/loopcloser.db" "$local_db"
        log_success "Database downloaded ($(du -h "$local_db" | cut -f1))"
    else
        log_warning "No database found in GCS, will create new one"
        touch "$local_db"
    fi
}

seed_database() {
    local env=$1
    shift
    local seed_flags=("$@")
    
    log_info "Running seed script: python scripts/seed_db.py --env ${env} ${seed_flags[*]}"
    
    # Activate virtual environment if it exists
    if [ -d "venv" ]; then
        source venv/bin/activate
    fi
    
    # Run seeding
    python scripts/seed_db.py --env "$env" "${seed_flags[@]}"
    
    log_success "Database seeded"
}

upload_database() {
    local bucket=$1
    local local_db=$2
    
    log_info "Uploading database to gs://${bucket}/loopcloser.db..."
    
    gsutil cp "$local_db" "gs://${bucket}/loopcloser.db"
    
    log_success "Database uploaded ($(du -h "$local_db" | cut -f1))"
}

cleanup() {
    local local_db=$1
    
    if [ -f "$local_db" ]; then
        log_info "Cleaning up local database file..."
        rm "$local_db"
    fi
}

# =============================================================================
# Main Script
# =============================================================================

main() {
    # Parse arguments
    if [ $# -lt 1 ]; then
        print_usage
        exit 1
    fi
    
    ENVIRONMENT=$1
    shift
    SEED_FLAGS=("$@")
    
    # Validate environment
    case "$ENVIRONMENT" in
        dev)
            SERVICE_NAME="loopcloser-dev"
            BUCKET="loopcloser-db-dev"
            LOCAL_DB="course_records_dev.db"
            ORIGINAL_MIN_INSTANCES=0
            ORIGINAL_MAX_INSTANCES=2
            ;;
        staging)
            SERVICE_NAME="loopcloser-staging"
            BUCKET="loopcloser-db-staging"
            LOCAL_DB="course_records_staging.db"
            ORIGINAL_MIN_INSTANCES=0
            ORIGINAL_MAX_INSTANCES=4
            ;;
        prod)
            SERVICE_NAME="loopcloser-prod"
            BUCKET="loopcloser-db-prod"
            LOCAL_DB="course_records_prod.db"
            ORIGINAL_MIN_INSTANCES=1
            ORIGINAL_MAX_INSTANCES=10
            ;;
        *)
            log_error "Invalid environment: $ENVIRONMENT"
            print_usage
            exit 1
            ;;
    esac
    
    # Print banner
    echo ""
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║  Remote Database Seeding - $(echo "$ENVIRONMENT" | tr '[:lower:]' '[:upper:]') Environment"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""
    
    # Run checks
    check_prerequisites
    confirm_action "$ENVIRONMENT" "$SERVICE_NAME" "${SEED_FLAGS[@]}"
    
    # Main workflow
    echo ""
    log_info "Starting remote database seeding workflow..."
    echo ""
    
    # Trap to ensure service is restored on exit
    trap "scale_service '$SERVICE_NAME' '$ORIGINAL_MIN_INSTANCES' '$ORIGINAL_MAX_INSTANCES' || true" EXIT
    
    # Step 1: Create backup
    create_backup "$BUCKET"
    
    # Step 2: Scale down service (set min to 0, keep max at original)
    # Note: Can't set max to 0 in Cloud Run, so we scale down min only
    # This allows instances to scale to zero but permits brief concurrent access if traffic arrives
    log_warning "Scaling service to min=0 (instances will scale down, brief concurrent access possible)"
    scale_service "$SERVICE_NAME" 0 "$ORIGINAL_MAX_INSTANCES"
    
    # Wait for instances to scale down
    log_info "Waiting 10 seconds for instances to scale down..."
    sleep 10
    
    # Step 3: Download database
    download_database "$BUCKET" "$LOCAL_DB"
    
    # Step 4: Seed database
    seed_database "$ENVIRONMENT" "${SEED_FLAGS[@]}"
    
    # Step 5: Upload database
    upload_database "$BUCKET" "$LOCAL_DB"
    
    # Step 6: Restart service to clear any cached database connections
    log_info "Forcing service restart to clear cached connections..."
    gcloud run services update "$SERVICE_NAME" \
        --region="$REGION" \
        --update-env-vars="LAST_SEED=$(date +%s)" \
        --quiet
    log_success "Service restarted with new database"
    
    # Step 7: Restore original scaling (handled by trap)
    scale_service "$SERVICE_NAME" "$ORIGINAL_MIN_INSTANCES" "$ORIGINAL_MAX_INSTANCES"
    
    # Step 8: Cleanup
    cleanup "$LOCAL_DB"
    
    # Step 9: Validate seeding (verify service can access the data)
    echo ""
    log_info "Validating seeding..."
    
    # Wait a moment for service to fully restart
    sleep 5
    
    # Try to query the health endpoint and then check if we can query user count
    SERVICE_URL="https://${ENVIRONMENT}.loopcloser.io"
    
    log_info "Checking service health at $SERVICE_URL/api/health..."
    if curl -sf "$SERVICE_URL/api/health" > /dev/null 2>&1; then
        log_success "Service is responding"
        
        # Download the database again to verify it matches what we uploaded
        log_info "Verifying database contents..."
        gsutil cp "gs://${BUCKET}/loopcloser.db" "/tmp/validate_${LOCAL_DB}"
        
        USER_COUNT=$(sqlite3 "/tmp/validate_${LOCAL_DB}" "SELECT COUNT(*) FROM users" 2>/dev/null || echo "0")
        rm "/tmp/validate_${LOCAL_DB}"
        
        if [ "$USER_COUNT" -gt 0 ]; then
            log_success "Database has $USER_COUNT users - seeding verified!"
        else
            log_warning "Database appears empty - seeding may not have worked"
        fi
    else
        log_warning "Service not responding yet - may take a few moments to start"
        log_info "Check manually: $SERVICE_URL"
    fi
    
    # Success message
    echo ""
    log_success "Remote database seeding complete!"
    echo ""
    log_info "Service URL: $SERVICE_URL"
    log_info "Backup location: gs://${BUCKET}/backups/"
    echo ""
    log_info "Demo credentials:"
    echo "  Email: loopcloser_demo_admin@proton.me"
    echo "  Password: Demo123!"
    echo ""
}

# Run main function
main "$@"
