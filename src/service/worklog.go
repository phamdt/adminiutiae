package service

import (
	"log"
	"net/http"
)

// WorklogService checks team worklogs via the admin API.
type WorklogService struct {
	baseURL string
	client  *http.Client
}

func NewWorklogService(baseURL string) *WorklogService {
	return &WorklogService{
		baseURL: baseURL,
		client:  &http.Client{},
	}
}

// CheckTempo performs a health check against the configured worklogs endpoint.
func (s *WorklogService) CheckTempo() {
	res, err := s.client.Get(s.baseURL)
	if err != nil {
		log.Printf("worklog check failed: %v", err)
		return
	}
	defer res.Body.Close()
	if res.StatusCode >= 300 {
		log.Printf("worklog check returned status %s", res.Status)
	}
}