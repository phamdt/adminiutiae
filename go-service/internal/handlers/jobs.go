package handlers

import (
	"context"
	"encoding/json"
	"net/http"
	"strconv"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/company/go-worker/internal/models"
	"github.com/company/go-worker/internal/workers"
	"github.com/company/go-worker/pkg/database"
	"github.com/company/go-worker/pkg/logger"
)

type JobHandler struct {
	processor *workers.JobProcessor
}

func NewJobHandler(processor *workers.JobProcessor) *JobHandler {
	return &JobHandler{
		processor: processor,
	}
}

func (h *JobHandler) ProcessJob(c *gin.Context) {
	var req models.JobRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		logger.Error().Err(err).Msg("Invalid job request")
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	logger.Info().
		Int("job_id", req.JobID).
		Int("user_id", req.UserID).
		Str("job_type", req.JobType).
		Msg("Received job processing request")

	// Process job asynchronously
	go func() {
		ctx, cancel := context.WithTimeout(context.Background(), 5*time.Minute)
		defer cancel()

		if err := h.processor.ProcessExternalDataJob(ctx, req.JobID, req.UserID, req.Parameters); err != nil {
			logger.Error().
				Err(err).
				Int("job_id", req.JobID).
				Msg("Failed to process job")
		}
	}()

	// Return immediately
	c.JSON(http.StatusOK, gin.H{
		"status":  "accepted",
		"job_id":  req.JobID,
		"message": "Job processing started",
	})
}

func (h *JobHandler) GetJobStatus(c *gin.Context) {
	jobIDStr := c.Param("id")
	jobID, err := strconv.Atoi(jobIDStr)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid job ID"})
		return
	}

	// Get job status from database
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	var job models.Job
	query := `
		SELECT id, user_id, job_type, status, parameters, 
			   COALESCE(result, '') as result, 
			   COALESCE(error_message, '') as error_message,
			   created_at, updated_at, completed_at
		FROM jobs WHERE id = $1
	`

	row := h.processor.GetDB().Pool.QueryRow(ctx, query, jobID)
	err = row.Scan(
		&job.ID, &job.UserID, &job.JobType, &job.Status, &job.Parameters,
		&job.Result, &job.ErrorMessage, &job.CreatedAt, &job.UpdatedAt, &job.CompletedAt,
	)

	if err != nil {
		logger.Error().Err(err).Int("job_id", jobID).Msg("Failed to get job from database")
		c.JSON(http.StatusNotFound, gin.H{"error": "Job not found"})
		return
	}

	// Parse result JSON if available
	var result interface{}
	if job.Result != "" {
		if err := json.Unmarshal([]byte(job.Result), &result); err != nil {
			logger.Error().Err(err).Msg("Failed to parse job result JSON")
			result = job.Result // Return as string if JSON parsing fails
		}
	}

	response := gin.H{
		"id":         job.ID,
		"user_id":    job.UserID,
		"job_type":   job.JobType,
		"status":     job.Status,
		"created_at": job.CreatedAt,
		"updated_at": job.UpdatedAt,
	}

	if result != nil {
		response["result"] = result
	}

	if job.ErrorMessage != "" {
		response["error_message"] = job.ErrorMessage
	}

	if job.CompletedAt != nil {
		response["completed_at"] = job.CompletedAt
	}

	c.JSON(http.StatusOK, response)
}

// Helper method to expose database for status queries
func (h *JobHandler) GetDB() *database.DB {
	// This is a temporary solution - in a real implementation,
	// you might want to inject the database separately
	return h.processor.GetDB()
}