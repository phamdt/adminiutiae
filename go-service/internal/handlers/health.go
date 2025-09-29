package handlers

import (
	"context"
	"net/http"
	"time"

	"github.com/company/go-worker/pkg/database"
	"github.com/company/go-worker/pkg/redis"
	"github.com/gin-gonic/gin"
)

type HealthHandler struct {
	db    *database.DB
	redis *redis.Client
}

func NewHealthHandler(db *database.DB, redis *redis.Client) *HealthHandler {
	return &HealthHandler{
		db:    db,
		redis: redis,
	}
}

func (h *HealthHandler) Check(c *gin.Context) {
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	response := gin.H{
		"status":  "healthy",
		"service": "go-worker",
		"version": "1.0.0",
	}

	// Check database connection
	if err := h.db.Ping(ctx); err != nil {
		response["status"] = "unhealthy"
		response["database"] = "down"
		response["error"] = err.Error()
		c.JSON(http.StatusServiceUnavailable, response)
		return
	}
	response["database"] = "connected"

	// Check Redis connection (optional)
	if h.redis != nil {
		if err := h.redis.Ping(ctx); err != nil {
			response["redis"] = "down"
			// Don't mark as unhealthy since Redis is optional
		} else {
			response["redis"] = "connected"
		}
	}

	// Add database statistics
	if stats := h.db.Stats(); stats != nil {
		response["database_stats"] = gin.H{
			"total_conns":       stats.TotalConns(),
			"acquired_conns":    stats.AcquiredConns(),
			"idle_conns":        stats.IdleConns(),
			"constructed_conns": stats.ConstructingConns(),
		}
	}

	c.JSON(http.StatusOK, response)
}

func (h *HealthHandler) Ready(c *gin.Context) {
	ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
	defer cancel()

	// Quick readiness check - just verify database is responding
	if err := h.db.Ping(ctx); err != nil {
		c.JSON(http.StatusServiceUnavailable, gin.H{
			"status": "not ready",
			"error":  err.Error(),
		})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"status": "ready",
	})
}
