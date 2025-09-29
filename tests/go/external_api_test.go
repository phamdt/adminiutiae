package tests

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/suite"
	"github.com/company/go-worker/internal/models"
	"github.com/company/go-worker/internal/services"
)

// ExternalAPITestSuite tests the external API service functionality
type ExternalAPITestSuite struct {
	suite.Suite
	service *services.ExternalAPIService
}

func (suite *ExternalAPITestSuite) SetupTest() {
	suite.service = services.NewExternalAPIService(30, 3) // 30s timeout, 3 retries
}

func TestExternalAPIService(t *testing.T) {
	suite.Run(t, new(ExternalAPITestSuite))
}

// Test successful API calls
func (suite *ExternalAPITestSuite) TestFetchExternalDataSuccess() {
	// Create mock HTTP server
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusOK)
		json.NewEncoder(w).Encode(map[string]interface{}{
			"id":    1,
			"title": "Test Post",
			"body":  "This is a test post",
		})
	}))
	defer server.Close()

	parameters := map[string]interface{}{
		"data_sources": []interface{}{server.URL},
		"filters":      map[string]interface{}{"test": true},
	}

	ctx := context.Background()
	results, err := suite.service.FetchExternalData(ctx, parameters)

	assert.NoError(suite.T(), err)
	assert.Len(suite.T(), results, 1)
	assert.Equal(suite.T(), "success", results[0].Status)
	assert.Equal(suite.T(), server.URL, results[0].Source)
	assert.NotNil(suite.T(), results[0].Data)
}

// Test multiple concurrent API calls
func (suite *ExternalAPITestSuite) TestFetchExternalDataMultipleSources() {
	// Create multiple mock servers
	servers := make([]*httptest.Server, 3)
	urls := make([]interface{}, 3)

	for i := 0; i < 3; i++ {
		index := i // Capture for closure
		servers[i] = httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			w.Header().Set("Content-Type", "application/json")
			w.WriteHeader(http.StatusOK)
			json.NewEncoder(w).Encode(map[string]interface{}{
				"id":     index + 1,
				"server": index + 1,
				"data":   "Test data from server " + string(rune(index+49)), // 1, 2, 3
			})
		}))
		urls[i] = servers[i].URL
	}

	// Cleanup
	defer func() {
		for _, server := range servers {
			server.Close()
		}
	}()

	parameters := map[string]interface{}{
		"data_sources": urls,
		"filters":      map[string]interface{}{},
	}

	ctx := context.Background()
	results, err := suite.service.FetchExternalData(ctx, parameters)

	assert.NoError(suite.T(), err)
	assert.Len(suite.T(), results, 3)

	// All should be successful
	successCount := 0
	for _, result := range results {
		if result.Status == "success" {
			successCount++
		}
	}
	assert.Equal(suite.T(), 3, successCount)
}

// Test API call failures and retries
func (suite *ExternalAPITestSuite) TestFetchExternalDataWithRetries() {
	attemptCount := 0
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		attemptCount++
		if attemptCount < 3 {
			// Fail first two attempts
			w.WriteHeader(http.StatusInternalServerError)
			return
		}
		// Succeed on third attempt
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusOK)
		json.NewEncoder(w).Encode(map[string]interface{}{
			"success": true,
			"attempt": attemptCount,
		})
	}))
	defer server.Close()

	parameters := map[string]interface{}{
		"data_sources": []interface{}{server.URL},
	}

	ctx := context.Background()
	results, err := suite.service.FetchExternalData(ctx, parameters)

	assert.NoError(suite.T(), err)
	assert.Len(suite.T(), results, 1)
	assert.Equal(suite.T(), "success", results[0].Status)
	assert.Equal(suite.T(), 3, attemptCount) // Should have retried twice
}

// Test API call with permanent failure
func (suite *ExternalAPITestSuite) TestFetchExternalDataPermanentFailure() {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusNotFound) // 4xx errors shouldn't retry
	}))
	defer server.Close()

	parameters := map[string]interface{}{
		"data_sources": []interface{}{server.URL},
	}

	ctx := context.Background()
	results, err := suite.service.FetchExternalData(ctx, parameters)

	assert.NoError(suite.T(), err) // Service returns results even with failures
	assert.Len(suite.T(), results, 1)
	assert.Equal(suite.T(), "error", results[0].Status)
	assert.Contains(suite.T(), results[0].Error, "404")
}

// Test timeout handling
func (suite *ExternalAPITestSuite) TestFetchExternalDataTimeout() {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		// Simulate slow response
		time.Sleep(2 * time.Second)
		w.WriteHeader(http.StatusOK)
	}))
	defer server.Close()

	// Create service with short timeout
	shortTimeoutService := services.NewExternalAPIService(1, 1) // 1s timeout, 1 retry

	parameters := map[string]interface{}{
		"data_sources": []interface{}{server.URL},
	}

	ctx := context.Background()
	results, err := shortTimeoutService.FetchExternalData(ctx, parameters)

	assert.NoError(suite.T(), err) // Service should handle timeout gracefully
	assert.Len(suite.T(), results, 1)
	assert.Equal(suite.T(), "error", results[0].Status)
	assert.Contains(suite.T(), results[0].Error, "timeout")
}

// Test context cancellation
func (suite *ExternalAPITestSuite) TestFetchExternalDataContextCancellation() {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		// Simulate slow response
		time.Sleep(1 * time.Second)
		w.WriteHeader(http.StatusOK)
	}))
	defer server.Close()

	parameters := map[string]interface{}{
		"data_sources": []interface{}{server.URL},
	}

	// Create context with short timeout
	ctx, cancel := context.WithTimeout(context.Background(), 100*time.Millisecond)
	defer cancel()

	results, err := suite.service.FetchExternalData(ctx, parameters)

	assert.NoError(suite.T(), err) // Service handles cancellation gracefully
	assert.Len(suite.T(), results, 1)
	assert.Equal(suite.T(), "error", results[0].Status)
	assert.Contains(suite.T(), results[0].Error, "context")
}

// Test invalid data sources
func (suite *ExternalAPITestSuite) TestFetchExternalDataInvalidDataSources() {
	testCases := []struct {
		name       string
		parameters map[string]interface{}
		expectErr  bool
	}{
		{
			name:       "missing data_sources",
			parameters: map[string]interface{}{"filters": map[string]interface{}{}},
			expectErr:  true,
		},
		{
			name:       "empty data_sources",
			parameters: map[string]interface{}{"data_sources": []interface{}{}},
			expectErr:  true,
		},
		{
			name: "non-string data_sources",
			parameters: map[string]interface{}{
				"data_sources": []interface{}{123, true, map[string]string{"url": "test"}},
			},
			expectErr: true,
		},
		{
			name: "mixed valid and invalid data_sources",
			parameters: map[string]interface{}{
				"data_sources": []interface{}{"http://valid.com", 123, "http://also-valid.com"},
			},
			expectErr: false, // Should process valid ones
		},
	}

	for _, tc := range testCases {
		suite.T().Run(tc.name, func(t *testing.T) {
			ctx := context.Background()
			results, err := suite.service.FetchExternalData(ctx, tc.parameters)

			if tc.expectErr {
				assert.Error(t, err)
			} else {
				assert.NoError(t, err)
				assert.NotNil(t, results)
			}
		})
	}
}

// Test malformed JSON responses
func (suite *ExternalAPITestSuite) TestFetchExternalDataMalformedJSON() {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusOK)
		w.Write([]byte("invalid json {"))
	}))
	defer server.Close()

	parameters := map[string]interface{}{
		"data_sources": []interface{}{server.URL},
	}

	ctx := context.Background()
	results, err := suite.service.FetchExternalData(ctx, parameters)

	assert.NoError(suite.T(), err) // Service handles JSON errors gracefully
	assert.Len(suite.T(), results, 1)
	assert.Equal(suite.T(), "error", results[0].Status)
	assert.Contains(suite.T(), results[0].Error, "invalid character")
}

// Test different content types
func (suite *ExternalAPITestSuite) TestFetchExternalDataDifferentContentTypes() {
	responses := map[string]func(w http.ResponseWriter, r *http.Request){
		"json": func(w http.ResponseWriter, r *http.Request) {
			w.Header().Set("Content-Type", "application/json")
			w.WriteHeader(http.StatusOK)
			json.NewEncoder(w).Encode(map[string]string{"type": "json"})
		},
		"xml": func(w http.ResponseWriter, r *http.Request) {
			w.Header().Set("Content-Type", "application/xml")
			w.WriteHeader(http.StatusOK)
			w.Write([]byte("<root><type>xml</type></root>"))
		},
		"plain": func(w http.ResponseWriter, r *http.Request) {
			w.Header().Set("Content-Type", "text/plain")
			w.WriteHeader(http.StatusOK)
			w.Write([]byte("plain text response"))
		},
	}

	for contentType, handler := range responses {
		suite.T().Run(contentType, func(t *testing.T) {
			server := httptest.NewServer(http.HandlerFunc(handler))
			defer server.Close()

			parameters := map[string]interface{}{
				"data_sources": []interface{}{server.URL},
			}

			ctx := context.Background()
			results, err := suite.service.FetchExternalData(ctx, parameters)

			assert.NoError(t, err)
			assert.Len(t, results, 1)

			// JSON should succeed, others might fail depending on implementation
			if contentType == "json" {
				assert.Equal(t, "success", results[0].Status)
			} else {
				// Non-JSON might be handled as error
				assert.Contains(t, []string{"success", "error"}, results[0].Status)
			}
		})
	}
}

// Test HTTP status codes
func (suite *ExternalAPITestSuite) TestFetchExternalDataHTTPStatusCodes() {
	statusCodes := []int{
		200, // OK
		201, // Created
		400, // Bad Request
		401, // Unauthorized
		403, // Forbidden
		404, // Not Found
		429, // Too Many Requests
		500, // Internal Server Error
		502, // Bad Gateway
		503, // Service Unavailable
	}

	for _, statusCode := range statusCodes {
		suite.T().Run(http.StatusText(statusCode), func(t *testing.T) {
			server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
				w.WriteHeader(statusCode)
				if statusCode == 200 || statusCode == 201 {
					json.NewEncoder(w).Encode(map[string]interface{}{"status": statusCode})
				}
			}))
			defer server.Close()

			parameters := map[string]interface{}{
				"data_sources": []interface{}{server.URL},
			}

			ctx := context.Background()
			results, err := suite.service.FetchExternalData(ctx, parameters)

			assert.NoError(t, err)
			assert.Len(t, results, 1)

			if statusCode == 200 || statusCode == 201 {
				assert.Equal(t, "success", results[0].Status)
			} else {
				assert.Equal(t, "error", results[0].Status)
				assert.Contains(t, results[0].Error, string(rune(statusCode/100+48))) // Contains status code
			}
		})
	}
}

// Test User-Agent and headers
func (suite *ExternalAPITestSuite) TestFetchExternalDataRequestHeaders() {
	var receivedHeaders http.Header
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		receivedHeaders = r.Header
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusOK)
		json.NewEncoder(w).Encode(map[string]string{"received": "ok"})
	}))
	defer server.Close()

	parameters := map[string]interface{}{
		"data_sources": []interface{}{server.URL},
	}

	ctx := context.Background()
	results, err := suite.service.FetchExternalData(ctx, parameters)

	assert.NoError(suite.T(), err)
	assert.Len(suite.T(), results, 1)
	assert.Equal(suite.T(), "success", results[0].Status)

	// Verify headers were set correctly
	assert.Equal(suite.T(), "Go-Worker/1.0", receivedHeaders.Get("User-Agent"))
	assert.Equal(suite.T(), "application/json", receivedHeaders.Get("Accept"))
}

// Test large response handling
func (suite *ExternalAPITestSuite) TestFetchExternalDataLargeResponse() {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusOK)

		// Create large response
		largeData := make([]map[string]interface{}, 1000)
		for i := 0; i < 1000; i++ {
			largeData[i] = map[string]interface{}{
				"id":    i,
				"data":  "Large data item with lots of text content to make response bigger",
				"index": i,
			}
		}

		json.NewEncoder(w).Encode(map[string]interface{}{
			"items": largeData,
			"total": 1000,
		})
	}))
	defer server.Close()

	parameters := map[string]interface{}{
		"data_sources": []interface{}{server.URL},
	}

	ctx := context.Background()
	results, err := suite.service.FetchExternalData(ctx, parameters)

	assert.NoError(suite.T(), err)
	assert.Len(suite.T(), results, 1)
	assert.Equal(suite.T(), "success", results[0].Status)

	// Verify large data was received
	data, ok := results[0].Data.(map[string]interface{})
	assert.True(suite.T(), ok)
	assert.Contains(suite.T(), data, "items")
}

// Test concurrent API calls with mixed success/failure
func (suite *ExternalAPITestSuite) TestFetchExternalDataMixedResults() {
	// Create servers with different behaviors
	successServer := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusOK)
		json.NewEncoder(w).Encode(map[string]string{"status": "success"})
	}))
	defer successServer.Close()

	errorServer := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusInternalServerError)
	}))
	defer errorServer.Close()

	slowServer := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		time.Sleep(2 * time.Second) // Will timeout
		w.WriteHeader(http.StatusOK)
	}))
	defer slowServer.Close()

	// Use short timeout service for timeout test
	shortTimeoutService := services.NewExternalAPIService(1, 1)

	parameters := map[string]interface{}{
		"data_sources": []interface{}{
			successServer.URL,
			errorServer.URL,
			slowServer.URL,
		},
	}

	ctx := context.Background()
	results, err := shortTimeoutService.FetchExternalData(ctx, parameters)

	assert.NoError(suite.T(), err)
	assert.Len(suite.T(), results, 3)

	// Count successes and failures
	successCount := 0
	errorCount := 0
	for _, result := range results {
		if result.Status == "success" {
			successCount++
		} else if result.Status == "error" {
			errorCount++
		}
	}

	assert.Equal(suite.T(), 1, successCount) // Only success server should succeed
	assert.Equal(suite.T(), 2, errorCount)   // Error server and timeout server should fail
}

// Test empty or invalid URLs
func (suite *ExternalAPITestSuite) TestFetchExternalDataInvalidURLs() {
	invalidURLs := []interface{}{
		"not-a-url",
		"ftp://unsupported-protocol.com",
		"",
		"http://",
		"https://",
	}

	parameters := map[string]interface{}{
		"data_sources": invalidURLs,
	}

	ctx := context.Background()
	results, err := suite.service.FetchExternalData(ctx, parameters)

	assert.NoError(suite.T(), err) // Service handles invalid URLs gracefully
	assert.Len(suite.T(), results, len(invalidURLs))

	// All should be errors
	for _, result := range results {
		assert.Equal(suite.T(), "error", result.Status)
		assert.NotEmpty(suite.T(), result.Error)
	}
}

// Test rate limiting simulation
func (suite *ExternalAPITestSuite) TestFetchExternalDataRateLimiting() {
	requestCount := 0
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		requestCount++
		if requestCount <= 2 {
			w.WriteHeader(http.StatusTooManyRequests)
			return
		}
		// Success after rate limit
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusOK)
		json.NewEncoder(w).Encode(map[string]string{"status": "ok"})
	}))
	defer server.Close()

	parameters := map[string]interface{}{
		"data_sources": []interface{}{server.URL},
	}

	ctx := context.Background()
	results, err := suite.service.FetchExternalData(ctx, parameters)

	assert.NoError(suite.T(), err)
	assert.Len(suite.T(), results, 1)
	assert.Equal(suite.T(), "success", results[0].Status)
	assert.True(suite.T(), requestCount >= 3) // Should have retried
}

// Test very large number of concurrent API calls
func (suite *ExternalAPITestSuite) TestFetchExternalDataHighConcurrency() {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusOK)
		json.NewEncoder(w).Encode(map[string]string{"response": "ok"})
	}))
	defer server.Close()

	// Create many data sources (all pointing to same server for simplicity)
	dataSources := make([]interface{}, 50)
	for i := 0; i < 50; i++ {
		dataSources[i] = server.URL
	}

	parameters := map[string]interface{}{
		"data_sources": dataSources,
	}

	ctx := context.Background()
	start := time.Now()
	results, err := suite.service.FetchExternalData(ctx, parameters)
	duration := time.Since(start)

	assert.NoError(suite.T(), err)
	assert.Len(suite.T(), results, 50)

	// All should be successful
	for _, result := range results {
		assert.Equal(suite.T(), "success", result.Status)
	}

	// Should complete in reasonable time due to concurrency
	assert.Less(suite.T(), duration.Seconds(), 10.0) // Should be much faster than 50 sequential calls
}

// Test response data structure validation
func (suite *ExternalAPITestSuite) TestFetchExternalDataResponseStructure() {
	testResponses := []map[string]interface{}{
		{"simple": "string"},
		{"number": 42},
		{"boolean": true},
		{"array": []interface{}{1, 2, 3}},
		{"nested": map[string]interface{}{"key": "value"}},
		{"complex": map[string]interface{}{
			"users": []interface{}{
				map[string]interface{}{"id": 1, "name": "John"},
				map[string]interface{}{"id": 2, "name": "Jane"},
			},
			"pagination": map[string]interface{}{
				"page":  1,
				"total": 100,
			},
		}},
	}

	for i, responseData := range testResponses {
		suite.T().Run(string(rune(i+48)), func(t *testing.T) { // Convert i to character
			server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
				w.Header().Set("Content-Type", "application/json")
				w.WriteHeader(http.StatusOK)
				json.NewEncoder(w).Encode(responseData)
			}))
			defer server.Close()

			parameters := map[string]interface{}{
				"data_sources": []interface{}{server.URL},
			}

			ctx := context.Background()
			results, err := suite.service.FetchExternalData(ctx, parameters)

			assert.NoError(t, err)
			assert.Len(t, results, 1)
			assert.Equal(t, "success", results[0].Status)

			// Verify data structure is preserved
			assert.Equal(t, responseData, results[0].Data)
		})
	}
}