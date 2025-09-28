package workers

import (
	"context"
	"encoding/json"
	"fmt"
	"time"

	"github.com/company/go-worker/internal/models"
	"github.com/company/go-worker/internal/services"
	"github.com/company/go-worker/pkg/database"
	"github.com/company/go-worker/pkg/logger"
	"github.com/company/go-worker/pkg/redis"
)

type JobProcessor struct {
	db         *database.DB
	redis      *redis.Client
	apiService *services.ExternalAPIService
}

func NewJobProcessor(db *database.DB, redis *redis.Client, apiService *services.ExternalAPIService) *JobProcessor {
	return &JobProcessor{
		db:         db,
		redis:      redis,
		apiService: apiService,
	}
}

func (jp *JobProcessor) ProcessExternalDataJob(ctx context.Context, jobID int, userID int, parameters map[string]interface{}) error {
	logger.Info().
		Int("job_id", jobID).
		Int("user_id", userID).
		Interface("parameters", parameters).
		Msg("Starting external data job processing")

	// Update job status to processing
	if err := jp.updateJobStatus(ctx, jobID, models.JobStatusProcessing, ""); err != nil {
		return fmt.Errorf("failed to update job status: %w", err)
	}

	// Fetch external data
	results, err := jp.apiService.FetchExternalData(ctx, parameters)
	if err != nil {
		// Update job with error
		if updateErr := jp.updateJobStatus(ctx, jobID, models.JobStatusFailed, err.Error()); updateErr != nil {
			logger.Error().Err(updateErr).Int("job_id", jobID).Msg("Failed to update job error status")
		}
		return fmt.Errorf("failed to fetch external data: %w", err)
	}

	// Check if we have any successful results
	hasSuccess := false
	for _, result := range results {
		if result.Status == "success" {
			hasSuccess = true
			break
		}
	}

	if !hasSuccess {
		errorMsg := "All external API calls failed"
		if updateErr := jp.updateJobStatus(ctx, jobID, models.JobStatusFailed, errorMsg); updateErr != nil {
			logger.Error().Err(updateErr).Int("job_id", jobID).Msg("Failed to update job error status")
		}
		return fmt.Errorf(errorMsg)
	}

	// Prepare result data
	resultData := map[string]interface{}{
		"api_results": results,
		"metadata": map[string]interface{}{
			"processed_at":    time.Now(),
			"total_sources":   len(results),
			"successful_calls": countSuccessfulResults(results),
			"job_id":         jobID,
			"user_id":        userID,
		},
	}

	// Store results
	resultJSON, err := json.Marshal(resultData)
	if err != nil {
		errorMsg := fmt.Sprintf("failed to marshal results: %v", err)
		if updateErr := jp.updateJobStatus(ctx, jobID, models.JobStatusFailed, errorMsg); updateErr != nil {
			logger.Error().Err(updateErr).Int("job_id", jobID).Msg("Failed to update job error status")
		}
		return fmt.Errorf("failed to marshal results: %w", err)
	}

	// Update job with results
	if err := jp.updateJobResult(ctx, jobID, string(resultJSON)); err != nil {
		return fmt.Errorf("failed to update job result: %w", err)
	}

	// Optional: Publish notification to Redis
	jp.publishJobUpdate(ctx, jobID, "completed")

	logger.Info().
		Int("job_id", jobID).
		Int("successful_calls", countSuccessfulResults(results)).
		Msg("External data job completed successfully")

	return nil
}

func (jp *JobProcessor) updateJobStatus(ctx context.Context, jobID int, status models.JobStatus, errorMessage string) error {
	query := `
		UPDATE jobs 
		SET status = $1, error_message = $2, updated_at = NOW()
		WHERE id = $3
	`
	_, err := jp.db.Pool.Exec(ctx, query, status, errorMessage, jobID)
	if err != nil {
		logger.Error().
			Err(err).
			Int("job_id", jobID).
			Str("status", string(status)).
			Msg("Failed to update job status")
	}
	return err
}

func (jp *JobProcessor) updateJobResult(ctx context.Context, jobID int, result string) error {
	query := `
		UPDATE jobs 
		SET status = $1, result = $2, updated_at = NOW(), completed_at = NOW()
		WHERE id = $3
	`
	_, err := jp.db.Pool.Exec(ctx, query, models.JobStatusCompleted, result, jobID)
	if err != nil {
		logger.Error().
			Err(err).
			Int("job_id", jobID).
			Msg("Failed to update job result")
	}
	return err
}

func (jp *JobProcessor) publishJobUpdate(ctx context.Context, jobID int, status string) {
	if jp.redis == nil {
		return // Redis is optional
	}

	updateData := map[string]interface{}{
		"job_id":    jobID,
		"status":    status,
		"timestamp": time.Now().Unix(),
	}

	data, err := json.Marshal(updateData)
	if err != nil {
		logger.Error().Err(err).Msg("Failed to marshal job update")
		return
	}

	channel := fmt.Sprintf("job_updates:%d", jobID)
	if err := jp.redis.Publish(ctx, channel, string(data)); err != nil {
		logger.Error().Err(err).Str("channel", channel).Msg("Failed to publish job update")
	}
}

func countSuccessfulResults(results []models.APIResult) int {
	count := 0
	for _, result := range results {
		if result.Status == "success" {
			count++
		}
	}
	return count
}

// GetDB returns the database instance for status queries
func (jp *JobProcessor) GetDB() *database.DB {
	return jp.db
}