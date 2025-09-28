package models

import (
	"time"
)

type Job struct {
	ID           int                    `json:"id" db:"id"`
	UserID       int                    `json:"user_id" db:"user_id"`
	JobType      string                 `json:"job_type" db:"job_type"`
	Status       string                 `json:"status" db:"status"`
	Parameters   string                 `json:"parameters" db:"parameters"`
	Result       string                 `json:"result" db:"result"`
	ErrorMessage string                 `json:"error_message" db:"error_message"`
	CreatedAt    time.Time              `json:"created_at" db:"created_at"`
	UpdatedAt    *time.Time             `json:"updated_at" db:"updated_at"`
	CompletedAt  *time.Time             `json:"completed_at" db:"completed_at"`
}

type JobStatus string

const (
	JobStatusQueued     JobStatus = "queued"
	JobStatusProcessing JobStatus = "processing"
	JobStatusCompleted  JobStatus = "completed"
	JobStatusFailed     JobStatus = "failed"
	JobStatusCancelled  JobStatus = "cancelled"
)

type JobRequest struct {
	JobID      int                    `json:"job_id"`
	UserID     int                    `json:"user_id"`
	JobType    string                 `json:"job_type"`
	Parameters map[string]interface{} `json:"parameters"`
}

type APIResult struct {
	Source string      `json:"source"`
	Data   interface{} `json:"data"`
	Status string      `json:"status"`
	Error  string      `json:"error,omitempty"`
}