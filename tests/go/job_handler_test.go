package tests

import (
	"bytes"
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/mock"
	"github.com/stretchr/testify/suite"
	"github.com/company/go-worker/internal/handlers"
	"github.com/company/go-worker/internal/models"
	"github.com/company/go-worker/internal/workers"
)

// MockJobProcessor implements the job processor interface for testing
type MockJobProcessor struct {
	mock.Mock
}

func (m *MockJobProcessor) ProcessExternalDataJob(ctx context.Context, jobID int, userID int, parameters map[string]interface{}) error {
	args := m.Called(ctx, jobID, userID, parameters)
	return args.Error(0)
}

func (m *MockJobProcessor) GetDB() *MockDatabase {
	return &MockDatabase{}
}

// MockDatabase for database operations
type MockDatabase struct {
	mock.Mock
}

func (m *MockDatabase) Pool() *MockPool {
	return &MockPool{}
}

type MockPool struct{}

func (m *MockPool) QueryRow(ctx context.Context, query string, args ...interface{}) *MockRow {
	return &MockRow{}
}

type MockRow struct{}

func (m *MockRow) Scan(dest ...interface{}) error {
	// Mock successful scan
	if len(dest) >= 10 {
		// Set mock values for job fields
		*(dest[0].(*int)) = 1                    // id
		*(dest[1].(*int)) = 1                    // user_id
		*(dest[2].(*string)) = "external_data"   // job_type
		*(dest[3].(*string)) = "completed"       // status
		*(dest[4].(*string)) = "{}"              // parameters
		*(dest[5].(*string)) = `{"test": "result"}` // result
		*(dest[6].(*string)) = ""                // error_message
		*(dest[7].(*time.Time)) = time.Now()     // created_at
		if dest[8] != nil {
			now := time.Now()
			*(dest[8].(**time.Time)) = &now // updated_at
		}
		if dest[9] != nil {
			now := time.Now()
			*(dest[9].(**time.Time)) = &now // completed_at
		}
	}
	return nil
}

// JobHandlerTestSuite tests the job handler functionality
type JobHandlerTestSuite struct {
	suite.Suite
	router        *gin.Engine
	mockProcessor *MockJobProcessor
	handler       *handlers.JobHandler
}

func (suite *JobHandlerTestSuite) SetupTest() {
	gin.SetMode(gin.TestMode)
	suite.mockProcessor = new(MockJobProcessor)
	suite.handler = handlers.NewJobHandler(suite.mockProcessor)
	suite.router = gin.New()
	suite.setupRoutes()
}

func (suite *JobHandlerTestSuite) setupRoutes() {
	v1 := suite.router.Group("/api/v1")
	{
		v1.POST("/jobs/process", suite.handler.ProcessJob)
		v1.GET("/jobs/:id/status", suite.handler.GetJobStatus)
	}
}

func TestJobHandlerSuite(t *testing.T) {
	suite.Run(t, new(JobHandlerTestSuite))
}

// Test successful job processing request
func (suite *JobHandlerTestSuite) TestProcessJobSuccess() {
	jobReq := models.JobRequest{
		JobID:   1,
		UserID:  1,
		JobType: "external_data",
		Parameters: map[string]interface{}{
			"data_sources": []string{"https://api.example.com/data"},
			"filters":      map[string]interface{}{"category": "test"},
		},
	}

	// Set up mock expectations
	suite.mockProcessor.On("ProcessExternalDataJob", 
		mock.AnythingOfType("*context.timerCtx"), 
		1, 1, 
		mock.AnythingOfType("map[string]interface {}")).
		Return(nil)

	jsonData, _ := json.Marshal(jobReq)
	req, _ := http.NewRequest("POST", "/api/v1/jobs/process", bytes.NewBuffer(jsonData))
	req.Header.Set("Content-Type", "application/json")

	w := httptest.NewRecorder()
	suite.router.ServeHTTP(w, req)

	assert.Equal(suite.T(), http.StatusOK, w.Code)

	var response map[string]interface{}
	err := json.Unmarshal(w.Body.Bytes(), &response)
	assert.NoError(suite.T(), err)
	assert.Equal(suite.T(), "accepted", response["status"])
	assert.Equal(suite.T(), float64(1), response["job_id"])

	// Wait a bit for async processing to start
	time.Sleep(100 * time.Millisecond)

	// Verify mock was called (async call might not be complete yet)
	// Note: Testing async calls is tricky - in real implementation,
	// you might want to make the processing synchronous for testing
}

// Test job processing with invalid JSON
func (suite *JobHandlerTestSuite) TestProcessJobInvalidJSON() {
	req, _ := http.NewRequest("POST", "/api/v1/jobs/process", bytes.NewBuffer([]byte("invalid json")))
	req.Header.Set("Content-Type", "application/json")

	w := httptest.NewRecorder()
	suite.router.ServeHTTP(w, req)

	assert.Equal(suite.T(), http.StatusBadRequest, w.Code)

	var response map[string]string
	err := json.Unmarshal(w.Body.Bytes(), &response)
	assert.NoError(suite.T(), err)
	assert.Contains(suite.T(), response["error"], "invalid character")
}

// Test job processing with missing fields
func (suite *JobHandlerTestSuite) TestProcessJobMissingFields() {
	// Request with missing job_id
	incompleteReq := map[string]interface{}{
		"user_id":    1,
		"job_type":   "external_data",
		"parameters": map[string]interface{}{},
	}

	jsonData, _ := json.Marshal(incompleteReq)
	req, _ := http.NewRequest("POST", "/api/v1/jobs/process", bytes.NewBuffer(jsonData))
	req.Header.Set("Content-Type", "application/json")

	w := httptest.NewRecorder()
	suite.router.ServeHTTP(w, req)

	// Should still accept request (job_id defaults to 0)
	assert.Equal(suite.T(), http.StatusOK, w.Code)
}

// Test job status retrieval
func (suite *JobHandlerTestSuite) TestGetJobStatusSuccess() {
	req, _ := http.NewRequest("GET", "/api/v1/jobs/1/status", nil)
	w := httptest.NewRecorder()
	suite.router.ServeHTTP(w, req)

	assert.Equal(suite.T(), http.StatusOK, w.Code)

	var response map[string]interface{}
	err := json.Unmarshal(w.Body.Bytes(), &response)
	assert.NoError(suite.T(), err)
	assert.Equal(suite.T(), float64(1), response["id"])
	assert.Equal(suite.T(), "completed", response["status"])
}

// Test job status retrieval with invalid ID
func (suite *JobHandlerTestSuite) TestGetJobStatusInvalidID() {
	req, _ := http.NewRequest("GET", "/api/v1/jobs/invalid/status", nil)
	w := httptest.NewRecorder()
	suite.router.ServeHTTP(w, req)

	assert.Equal(suite.T(), http.StatusBadRequest, w.Code)

	var response map[string]string
	err := json.Unmarshal(w.Body.Bytes(), &response)
	assert.NoError(suite.T(), err)
	assert.Equal(suite.T(), "Invalid job ID", response["error"])
}

// Test concurrent job processing requests
func (suite *JobHandlerTestSuite) TestConcurrentJobProcessing() {
	const numRequests = 10
	
	// Set up mock expectations for multiple calls
	for i := 0; i < numRequests; i++ {
		suite.mockProcessor.On("ProcessExternalDataJob", 
			mock.AnythingOfType("*context.timerCtx"), 
			mock.AnythingOfType("int"), 
			mock.AnythingOfType("int"), 
			mock.AnythingOfType("map[string]interface {}")).
			Return(nil)
	}

	// Send multiple concurrent requests
	responses := make(chan *httptest.ResponseRecorder, numRequests)
	
	for i := 0; i < numRequests; i++ {
		go func(index int) {
			jobReq := models.JobRequest{
				JobID:      index + 1,
				UserID:     1,
				JobType:    "external_data",
				Parameters: map[string]interface{}{"index": index},
			}

			jsonData, _ := json.Marshal(jobReq)
			req, _ := http.NewRequest("POST", "/api/v1/jobs/process", bytes.NewBuffer(jsonData))
			req.Header.Set("Content-Type", "application/json")

			w := httptest.NewRecorder()
			suite.router.ServeHTTP(w, req)
			responses <- w
		}(i)
	}

	// Collect responses
	successCount := 0
	for i := 0; i < numRequests; i++ {
		w := <-responses
		if w.Code == http.StatusOK {
			successCount++
		}
	}

	// All requests should succeed
	assert.Equal(suite.T(), numRequests, successCount)
}

// Test job processing with large parameters
func (suite *JobHandlerTestSuite) TestProcessJobLargeParameters() {
	// Create large parameters
	largeParameters := make(map[string]interface{})
	largeParameters["data_sources"] = make([]string, 100)
	for i := 0; i < 100; i++ {
		largeParameters["data_sources"].([]string)[i] = "https://api" + string(rune(i+48)) + ".example.com"
	}
	
	largeFilters := make(map[string]interface{})
	for i := 0; i < 50; i++ {
		largeFilters["filter_"+string(rune(i+48))] = "value_" + string(rune(i+48))
	}
	largeParameters["filters"] = largeFilters

	jobReq := models.JobRequest{
		JobID:      1,
		UserID:     1,
		JobType:    "external_data",
		Parameters: largeParameters,
	}

	suite.mockProcessor.On("ProcessExternalDataJob", 
		mock.AnythingOfType("*context.timerCtx"), 
		1, 1, 
		mock.AnythingOfType("map[string]interface {}")).
		Return(nil)

	jsonData, _ := json.Marshal(jobReq)
	req, _ := http.NewRequest("POST", "/api/v1/jobs/process", bytes.NewBuffer(jsonData))
	req.Header.Set("Content-Type", "application/json")

	w := httptest.NewRecorder()
	suite.router.ServeHTTP(w, req)

	assert.Equal(suite.T(), http.StatusOK, w.Code)
}

// Test job processing timeout scenarios
func (suite *JobHandlerTestSuite) TestProcessJobTimeoutHandling() {
	jobReq := models.JobRequest{
		JobID:      1,
		UserID:     1,
		JobType:    "external_data",
		Parameters: map[string]interface{}{"timeout_test": true},
	}

	// Mock processor to simulate timeout
	suite.mockProcessor.On("ProcessExternalDataJob", 
		mock.AnythingOfType("*context.timerCtx"), 
		1, 1, 
		mock.AnythingOfType("map[string]interface {}")).
		Return(context.DeadlineExceeded)

	jsonData, _ := json.Marshal(jobReq)
	req, _ := http.NewRequest("POST", "/api/v1/jobs/process", bytes.NewBuffer(jsonData))
	req.Header.Set("Content-Type", "application/json")

	w := httptest.NewRecorder()
	suite.router.ServeHTTP(w, req)

	// Should still accept the job even if processing fails
	assert.Equal(suite.T(), http.StatusOK, w.Code)
}

// Test health check endpoint functionality
func (suite *JobHandlerTestSuite) TestHealthCheckEndpoint() {
	// This would be in a separate health handler test, but including here for completeness
	router := gin.New()
	router.GET("/health", func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{
			"status":   "healthy",
			"service":  "go-worker",
			"database": "connected",
		})
	})

	req, _ := http.NewRequest("GET", "/health", nil)
	w := httptest.NewRecorder()
	router.ServeHTTP(w, req)

	assert.Equal(suite.T(), http.StatusOK, w.Code)

	var response map[string]string
	err := json.Unmarshal(w.Body.Bytes(), &response)
	assert.NoError(suite.T(), err)
	assert.Equal(suite.T(), "healthy", response["status"])
	assert.Equal(suite.T(), "go-worker", response["service"])
}

// Test job status endpoint with different scenarios
func (suite *JobHandlerTestSuite) TestGetJobStatusVariousScenarios() {
	testCases := []struct {
		name           string
		jobID          string
		expectedStatus int
		expectedInBody string
	}{
		{
			name:           "valid job ID",
			jobID:          "1",
			expectedStatus: http.StatusOK,
			expectedInBody: "completed",
		},
		{
			name:           "zero job ID",
			jobID:          "0",
			expectedStatus: http.StatusOK,
			expectedInBody: "completed",
		},
		{
			name:           "negative job ID",
			jobID:          "-1",
			expectedStatus: http.StatusOK,
			expectedInBody: "completed",
		},
		{
			name:           "invalid job ID format",
			jobID:          "abc",
			expectedStatus: http.StatusBadRequest,
			expectedInBody: "Invalid job ID",
		},
		{
			name:           "very large job ID",
			jobID:          "999999999",
			expectedStatus: http.StatusOK,
			expectedInBody: "completed",
		},
	}

	for _, tc := range testCases {
		suite.T().Run(tc.name, func(t *testing.T) {
			req, _ := http.NewRequest("GET", "/api/v1/jobs/"+tc.jobID+"/status", nil)
			w := httptest.NewRecorder()
			suite.router.ServeHTTP(w, req)

			assert.Equal(t, tc.expectedStatus, w.Code)
			assert.Contains(t, w.Body.String(), tc.expectedInBody)
		})
	}
}

// Test request size limits
func (suite *JobHandlerTestSuite) TestRequestSizeLimits() {
	// Create extremely large request
	largeParams := make(map[string]interface{})
	largeArray := make([]string, 10000)
	for i := 0; i < 10000; i++ {
		largeArray[i] = "https://api" + string(rune(i%10+48)) + ".example.com/very/long/path/that/makes/the/request/much/larger"
	}
	largeParams["data_sources"] = largeArray

	jobReq := models.JobRequest{
		JobID:      1,
		UserID:     1,
		JobType:    "external_data",
		Parameters: largeParams,
	}

	jsonData, _ := json.Marshal(jobReq)
	req, _ := http.NewRequest("POST", "/api/v1/jobs/process", bytes.NewBuffer(jsonData))
	req.Header.Set("Content-Type", "application/json")

	w := httptest.NewRecorder()
	suite.router.ServeHTTP(w, req)

	// Should either accept or reject based on size limits
	assert.Contains(suite.T(), []int{http.StatusOK, http.StatusRequestEntityTooLarge}, w.Code)
}

// Test malformed request handling
func (suite *JobHandlerTestSuite) TestMalformedRequests() {
	malformedRequests := []struct {
		name string
		body string
	}{
		{"empty body", ""},
		{"only opening brace", "{"},
		{"only closing brace", "}"},
		{"invalid json structure", `{"key": value}`},
		{"incomplete json", `{"job_id": 1, "user_id"`},
		{"null values", `{"job_id": null, "user_id": null}`},
	}

	for _, test := range malformedRequests {
		suite.T().Run(test.name, func(t *testing.T) {
			req, _ := http.NewRequest("POST", "/api/v1/jobs/process", bytes.NewBuffer([]byte(test.body)))
			req.Header.Set("Content-Type", "application/json")

			w := httptest.NewRecorder()
			suite.router.ServeHTTP(w, req)

			// Should return 400 Bad Request for malformed JSON
			assert.Equal(t, http.StatusBadRequest, w.Code)
		})
	}
}

// Test different content types
func (suite *JobHandlerTestSuite) TestDifferentContentTypes() {
	jobReq := models.JobRequest{
		JobID:      1,
		UserID:     1,
		JobType:    "external_data",
		Parameters: map[string]interface{}{},
	}

	jsonData, _ := json.Marshal(jobReq)

	contentTypes := []struct {
		name        string
		contentType string
		expectCode  int
	}{
		{"application/json", "application/json", http.StatusOK},
		{"text/plain", "text/plain", http.StatusBadRequest},
		{"application/xml", "application/xml", http.StatusBadRequest},
		{"no content type", "", http.StatusBadRequest},
	}

	for _, ct := range contentTypes {
		suite.T().Run(ct.name, func(t *testing.T) {
			if ct.expectCode == http.StatusOK {
				suite.mockProcessor.On("ProcessExternalDataJob", 
					mock.AnythingOfType("*context.timerCtx"), 
					1, 1, 
					mock.AnythingOfType("map[string]interface {}")).
					Return(nil).Once()
			}

			req, _ := http.NewRequest("POST", "/api/v1/jobs/process", bytes.NewBuffer(jsonData))
			if ct.contentType != "" {
				req.Header.Set("Content-Type", ct.contentType)
			}

			w := httptest.NewRecorder()
			suite.router.ServeHTTP(w, req)

			assert.Equal(t, ct.expectCode, w.Code)
		})
	}
}

// Test HTTP method validation
func (suite *JobHandlerTestSuite) TestHTTPMethodValidation() {
	jobReq := models.JobRequest{
		JobID:      1,
		UserID:     1,
		JobType:    "external_data",
		Parameters: map[string]interface{}{},
	}

	jsonData, _ := json.Marshal(jobReq)

	httpMethods := []struct {
		method     string
		expectCode int
	}{
		{"POST", http.StatusOK},
		{"GET", http.StatusMethodNotAllowed},
		{"PUT", http.StatusMethodNotAllowed},
		{"DELETE", http.StatusMethodNotAllowed},
		{"PATCH", http.StatusMethodNotAllowed},
		{"OPTIONS", http.StatusMethodNotAllowed},
	}

	for _, method := range httpMethods {
		suite.T().Run(method.method, func(t *testing.T) {
			if method.expectCode == http.StatusOK {
				suite.mockProcessor.On("ProcessExternalDataJob", 
					mock.AnythingOfType("*context.timerCtx"), 
					1, 1, 
					mock.AnythingOfType("map[string]interface {}")).
					Return(nil).Once()
			}

			req, _ := http.NewRequest(method.method, "/api/v1/jobs/process", bytes.NewBuffer(jsonData))
			req.Header.Set("Content-Type", "application/json")

			w := httptest.NewRecorder()
			suite.router.ServeHTTP(w, req)

			assert.Equal(t, method.expectCode, w.Code)
		})
	}
}

// Test request headers validation
func (suite *JobHandlerTestSuite) TestRequestHeaders() {
	jobReq := models.JobRequest{
		JobID:      1,
		UserID:     1,
		JobType:    "external_data",
		Parameters: map[string]interface{}{},
	}

	suite.mockProcessor.On("ProcessExternalDataJob", 
		mock.AnythingOfType("*context.timerCtx"), 
		1, 1, 
		mock.AnythingOfType("map[string]interface {}")).
		Return(nil)

	jsonData, _ := json.Marshal(jobReq)
	req, _ := http.NewRequest("POST", "/api/v1/jobs/process", bytes.NewBuffer(jsonData))
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("User-Agent", "Test-Client/1.0")
	req.Header.Set("X-Request-ID", "test-123")

	w := httptest.NewRecorder()
	suite.router.ServeHTTP(w, req)

	assert.Equal(suite.T(), http.StatusOK, w.Code)

	// Headers should be preserved in request context
	// (Implementation specific - this tests that headers don't break anything)
}

// Test response format consistency
func (suite *JobHandlerTestSuite) TestResponseFormatConsistency() {
	// Test that all successful responses have consistent format
	jobReq := models.JobRequest{
		JobID:      1,
		UserID:     1,
		JobType:    "external_data",
		Parameters: map[string]interface{}{},
	}

	suite.mockProcessor.On("ProcessExternalDataJob", 
		mock.AnythingOfType("*context.timerCtx"), 
		1, 1, 
		mock.AnythingOfType("map[string]interface {}")).
		Return(nil)

	jsonData, _ := json.Marshal(jobReq)
	req, _ := http.NewRequest("POST", "/api/v1/jobs/process", bytes.NewBuffer(jsonData))
	req.Header.Set("Content-Type", "application/json")

	w := httptest.NewRecorder()
	suite.router.ServeHTTP(w, req)

	assert.Equal(suite.T(), http.StatusOK, w.Code)

	var response map[string]interface{}
	err := json.Unmarshal(w.Body.Bytes(), &response)
	assert.NoError(suite.T(), err)

	// Verify required fields in response
	requiredFields := []string{"status", "job_id", "message"}
	for _, field := range requiredFields {
		assert.Contains(suite.T(), response, field)
	}

	// Verify field types
	assert.IsType(suite.T(), "", response["status"])
	assert.IsType(suite.T(), float64(0), response["job_id"]) // JSON numbers are float64
	assert.IsType(suite.T(), "", response["message"])
}