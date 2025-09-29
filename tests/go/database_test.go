package tests

import (
	"context"
	"testing"
	"time"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/suite"
	"github.com/company/go-worker/pkg/database"
)

// DatabaseTestSuite tests database connectivity and operations
type DatabaseTestSuite struct {
	suite.Suite
	db *database.DB
}

func (suite *DatabaseTestSuite) SetupSuite() {
	// Use test database URL
	testDBURL := "postgresql://testuser:testpass@localhost:5433/testdb"
	
	db, err := database.NewDB(testDBURL)
	if err != nil {
		suite.T().Skip("Test database not available, skipping database tests")
		return
	}
	
	suite.db = db
}

func (suite *DatabaseTestSuite) TearDownSuite() {
	if suite.db != nil {
		suite.db.Close()
	}
}

func TestDatabaseSuite(t *testing.T) {
	suite.Run(t, new(DatabaseTestSuite))
}

// Test database connection
func (suite *DatabaseTestSuite) TestDatabaseConnection() {
	if suite.db == nil {
		suite.T().Skip("Database not available")
		return
	}

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	err := suite.db.Ping(ctx)
	assert.NoError(suite.T(), err)
}

// Test connection pool statistics
func (suite *DatabaseTestSuite) TestConnectionPoolStats() {
	if suite.db == nil {
		suite.T().Skip("Database not available")
		return
	}

	stats := suite.db.Stats()
	assert.NotNil(suite.T(), stats)
	
	// Should have some basic pool configuration
	assert.True(suite.T(), stats.MaxConns() > 0)
	assert.True(suite.T(), stats.MaxConns() >= stats.MinConns())
}

// Test job status update operations
func (suite *DatabaseTestSuite) TestJobStatusUpdate() {
	if suite.db == nil {
		suite.T().Skip("Database not available")
		return
	}

	ctx := context.Background()

	// First, insert a test job (assuming jobs table exists)
	insertQuery := `
		INSERT INTO jobs (user_id, job_type, status, parameters, created_at)
		VALUES ($1, $2, $3, $4, NOW())
		RETURNING id
	`
	
	var jobID int
	err := suite.db.Pool.QueryRow(ctx, insertQuery, 1, "external_data", "queued", "{}").Scan(&jobID)
	if err != nil {
		suite.T().Skip("Jobs table not available or not properly set up")
		return
	}

	// Test status update
	updateQuery := `
		UPDATE jobs 
		SET status = $1, updated_at = NOW()
		WHERE id = $2
	`
	
	_, err = suite.db.Pool.Exec(ctx, updateQuery, "processing", jobID)
	assert.NoError(suite.T(), err)

	// Verify update
	selectQuery := `SELECT status FROM jobs WHERE id = $1`
	var status string
	err = suite.db.Pool.QueryRow(ctx, selectQuery, jobID).Scan(&status)
	assert.NoError(suite.T(), err)
	assert.Equal(suite.T(), "processing", status)

	// Cleanup
	_, err = suite.db.Pool.Exec(ctx, "DELETE FROM jobs WHERE id = $1", jobID)
	assert.NoError(suite.T(), err)
}

// Test job result update operations
func (suite *DatabaseTestSuite) TestJobResultUpdate() {
	if suite.db == nil {
		suite.T().Skip("Database not available")
		return
	}

	ctx := context.Background()

	// Insert test job
	insertQuery := `
		INSERT INTO jobs (user_id, job_type, status, parameters, created_at)
		VALUES ($1, $2, $3, $4, NOW())
		RETURNING id
	`
	
	var jobID int
	err := suite.db.Pool.QueryRow(ctx, insertQuery, 1, "external_data", "processing", "{}").Scan(&jobID)
	if err != nil {
		suite.T().Skip("Jobs table not available")
		return
	}

	// Test result update
	resultData := `{"api_results": [{"source": "test", "data": "result"}], "metadata": {"processed_at": "2023-01-01T00:00:00Z"}}`
	updateQuery := `
		UPDATE jobs 
		SET status = $1, result = $2, completed_at = NOW(), updated_at = NOW()
		WHERE id = $3
	`
	
	_, err = suite.db.Pool.Exec(ctx, updateQuery, "completed", resultData, jobID)
	assert.NoError(suite.T(), err)

	// Verify update
	selectQuery := `SELECT status, result, completed_at FROM jobs WHERE id = $1`
	var status, result string
	var completedAt *time.Time
	err = suite.db.Pool.QueryRow(ctx, selectQuery, jobID).Scan(&status, &result, &completedAt)
	assert.NoError(suite.T(), err)
	
	assert.Equal(suite.T(), "completed", status)
	assert.Equal(suite.T(), resultData, result)
	assert.NotNil(suite.T(), completedAt)

	// Cleanup
	_, err = suite.db.Pool.Exec(ctx, "DELETE FROM jobs WHERE id = $1", jobID)
	assert.NoError(suite.T(), err)
}

// Test database transaction handling
func (suite *DatabaseTestSuite) TestDatabaseTransaction() {
	if suite.db == nil {
		suite.T().Skip("Database not available")
		return
	}

	ctx := context.Background()

	// Begin transaction
	tx, err := suite.db.Pool.Begin(ctx)
	assert.NoError(suite.T(), err)

	// Insert job within transaction
	insertQuery := `
		INSERT INTO jobs (user_id, job_type, status, parameters, created_at)
		VALUES ($1, $2, $3, $4, NOW())
		RETURNING id
	`
	
	var jobID int
	err = tx.QueryRow(ctx, insertQuery, 1, "transaction_test", "queued", "{}").Scan(&jobID)
	if err != nil {
		tx.Rollback(ctx)
		suite.T().Skip("Cannot test transactions without jobs table")
		return
	}

	// Job should exist within transaction
	var count int
	err = tx.QueryRow(ctx, "SELECT COUNT(*) FROM jobs WHERE id = $1", jobID).Scan(&count)
	assert.NoError(suite.T(), err)
	assert.Equal(suite.T(), 1, count)

	// Rollback transaction
	err = tx.Rollback(ctx)
	assert.NoError(suite.T(), err)

	// Job should not exist after rollback
	err = suite.db.Pool.QueryRow(ctx, "SELECT COUNT(*) FROM jobs WHERE id = $1", jobID).Scan(&count)
	assert.NoError(suite.T(), err)
	assert.Equal(suite.T(), 0, count)
}

// Test connection timeout handling
func (suite *DatabaseTestSuite) TestConnectionTimeout() {
	if suite.db == nil {
		suite.T().Skip("Database not available")
		return
	}

	// Create context with very short timeout
	ctx, cancel := context.WithTimeout(context.Background(), 1*time.Millisecond)
	defer cancel()

	// This should timeout
	err := suite.db.Ping(ctx)
	assert.Error(suite.T(), err)
	assert.Contains(suite.T(), err.Error(), "context deadline exceeded")
}

// Test connection pool behavior under load
func (suite *DatabaseTestSuite) TestConnectionPoolUnderLoad() {
	if suite.db == nil {
		suite.T().Skip("Database not available")
		return
	}

	ctx := context.Background()

	// Create multiple concurrent database operations
	const numOperations = 20
	results := make(chan error, numOperations)

	for i := 0; i < numOperations; i++ {
		go func() {
			err := suite.db.Ping(ctx)
			results <- err
		}()
	}

	// Collect results
	errorCount := 0
	for i := 0; i < numOperations; i++ {
		err := <-results
		if err != nil {
			errorCount++
		}
	}

	// Most operations should succeed
	assert.True(suite.T(), errorCount < numOperations/2, "Too many database operations failed under load")
}

// Test database connection recovery
func (suite *DatabaseTestSuite) TestConnectionRecovery() {
	if suite.db == nil {
		suite.T().Skip("Database not available")
		return
	}

	ctx := context.Background()

	// First ping should work
	err := suite.db.Ping(ctx)
	assert.NoError(suite.T(), err)

	// Simulate connection issues by using invalid context
	invalidCtx, cancel := context.WithCancel(context.Background())
	cancel() // Cancel immediately

	err = suite.db.Ping(invalidCtx)
	assert.Error(suite.T(), err)

	// Connection should recover for new requests
	err = suite.db.Ping(ctx)
	assert.NoError(suite.T(), err)
}

// Test SQL injection prevention
func (suite *DatabaseTestSuite) TestSQLInjectionPrevention() {
	if suite.db == nil {
		suite.T().Skip("Database not available")
		return
	}

	ctx := context.Background()

	// Test parameterized queries prevent SQL injection
	maliciousInputs := []string{
		"'; DROP TABLE jobs; --",
		"1; UPDATE jobs SET status = 'hacked'; --",
		"1 OR 1=1",
		"1 UNION SELECT * FROM users",
	}

	for _, maliciousInput := range maliciousInputs {
		// Use parameterized query (safe)
		query := "SELECT COUNT(*) FROM jobs WHERE user_id = $1"
		var count int
		err := suite.db.Pool.QueryRow(ctx, query, maliciousInput).Scan(&count)
		
		// Should not cause SQL injection (might error due to type conversion)
		// The important thing is that it doesn't execute malicious SQL
		if err != nil {
			// Type conversion error is expected and safe
			assert.Contains(suite.T(), err.Error(), "invalid input")
		} else {
			// If it succeeds, count should be 0 (no user with that ID)
			assert.Equal(suite.T(), 0, count)
		}
	}
}

// Benchmark test for database operations
func (suite *DatabaseTestSuite) TestDatabaseOperationPerformance() {
	if suite.db == nil {
		suite.T().Skip("Database not available")
		return
	}

	ctx := context.Background()

	// Test simple query performance
	start := time.Now()
	
	for i := 0; i < 100; i++ {
		var result int
		err := suite.db.Pool.QueryRow(ctx, "SELECT 1").Scan(&result)
		assert.NoError(suite.T(), err)
		assert.Equal(suite.T(), 1, result)
	}

	duration := time.Since(start)

	// 100 simple queries should complete quickly
	assert.Less(suite.T(), duration.Seconds(), 1.0, "Database operations are too slow")
}