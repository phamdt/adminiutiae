package services

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"sync"
	"time"

	"github.com/company/go-worker/internal/models"
	"github.com/company/go-worker/pkg/logger"
)

type ExternalAPIService struct {
	client     *http.Client
	maxRetries int
}

func NewExternalAPIService(httpTimeout int, maxRetries int) *ExternalAPIService {
	return &ExternalAPIService{
		client: &http.Client{
			Timeout: time.Duration(httpTimeout) * time.Second,
		},
		maxRetries: maxRetries,
	}
}

func (s *ExternalAPIService) FetchExternalData(ctx context.Context, parameters map[string]interface{}) ([]models.APIResult, error) {
	logger.Info().
		Interface("parameters", parameters).
		Msg("Starting external data fetch")

	// Extract data sources from parameters
	dataSources, ok := parameters["data_sources"].([]interface{})
	if !ok {
		return nil, fmt.Errorf("data_sources not found or invalid format")
	}

	// Convert to string slice
	var urls []string
	for _, source := range dataSources {
		if url, ok := source.(string); ok {
			urls = append(urls, url)
		}
	}

	if len(urls) == 0 {
		return nil, fmt.Errorf("no valid URLs found in data_sources")
	}

	// Fetch data concurrently from all sources
	var wg sync.WaitGroup
	results := make(chan models.APIResult, len(urls))

	for _, url := range urls {
		wg.Add(1)
		go func(apiURL string) {
			defer wg.Done()
			result := s.fetchFromURL(ctx, apiURL)
			results <- result
		}(url)
	}

	// Wait for all goroutines to complete
	go func() {
		wg.Wait()
		close(results)
	}()

	// Collect results
	var apiResults []models.APIResult
	for result := range results {
		apiResults = append(apiResults, result)
	}

	logger.Info().
		Int("total_sources", len(urls)).
		Int("successful_results", countSuccessful(apiResults)).
		Msg("External data fetch completed")

	return apiResults, nil
}

func (s *ExternalAPIService) fetchFromURL(ctx context.Context, url string) models.APIResult {
	logger.Debug().Str("url", url).Msg("Fetching data from URL")

	var lastErr error
	for attempt := 1; attempt <= s.maxRetries; attempt++ {
		select {
		case <-ctx.Done():
			return models.APIResult{
				Source: url,
				Status: "error",
				Error:  "context cancelled",
			}
		default:
		}

		req, err := http.NewRequestWithContext(ctx, "GET", url, nil)
		if err != nil {
			lastErr = err
			continue
		}

		// Set headers
		req.Header.Set("User-Agent", "Go-Worker/1.0")
		req.Header.Set("Accept", "application/json")

		resp, err := s.client.Do(req)
		if err != nil {
			lastErr = err
			if attempt < s.maxRetries {
				logger.Warn().
					Str("url", url).
					Int("attempt", attempt).
					Err(err).
					Msg("Request failed, retrying")
				time.Sleep(time.Duration(attempt) * time.Second)
				continue
			}
			break
		}
		defer resp.Body.Close()

		if resp.StatusCode != http.StatusOK {
			lastErr = fmt.Errorf("HTTP %d", resp.StatusCode)
			if attempt < s.maxRetries && resp.StatusCode >= 500 {
				logger.Warn().
					Str("url", url).
					Int("status_code", resp.StatusCode).
					Int("attempt", attempt).
					Msg("Server error, retrying")
				time.Sleep(time.Duration(attempt) * time.Second)
				continue
			}
			break
		}

		// Parse JSON response
		var data interface{}
		if err := json.NewDecoder(resp.Body).Decode(&data); err != nil {
			lastErr = err
			break
		}

		logger.Debug().
			Str("url", url).
			Msg("Successfully fetched data")

		return models.APIResult{
			Source: url,
			Data:   data,
			Status: "success",
		}
	}

	logger.Error().
		Str("url", url).
		Err(lastErr).
		Int("attempts", s.maxRetries).
		Msg("Failed to fetch data after all retries")

	return models.APIResult{
		Source: url,
		Status: "error",
		Error:  lastErr.Error(),
	}
}

func countSuccessful(results []models.APIResult) int {
	count := 0
	for _, result := range results {
		if result.Status == "success" {
			count++
		}
	}
	return count
}
