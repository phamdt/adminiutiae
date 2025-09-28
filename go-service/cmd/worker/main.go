package main

import (
	"context"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/company/go-worker/internal/config"
	"github.com/company/go-worker/internal/handlers"
	"github.com/company/go-worker/internal/services"
	"github.com/company/go-worker/internal/workers"
	"github.com/company/go-worker/pkg/database"
	"github.com/company/go-worker/pkg/logger"
	"github.com/company/go-worker/pkg/redis"
)

func main() {
	// Initialize configuration
	cfg := config.Load()

	// Initialize logger
	logger.Init(cfg.LogLevel)
	logger.Info().Msg("Starting Go worker service")

	// Initialize database
	db, err := database.NewDB(cfg.DatabaseURL)
	if err != nil {
		logger.Error().Err(err).Msg("Failed to connect to database")
		os.Exit(1)
	}
	defer db.Close()

	// Initialize Redis (optional)
	var redisClient *redis.Client
	if cfg.RedisURL != "" {
		redisClient, err = redis.NewClient(cfg.RedisURL)
		if err != nil {
			logger.Warn().Err(err).Msg("Failed to connect to Redis, continuing without it")
		} else {
			defer redisClient.Close()
			logger.Info().Msg("Connected to Redis")
		}
	}

	// Test database connection
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	if err := db.Ping(ctx); err != nil {
		logger.Error().Err(err).Msg("Failed to ping database")
		os.Exit(1)
	}

	logger.Info().Msg("Connected to database successfully")

	// Initialize services
	apiService := services.NewExternalAPIService(cfg.HTTPTimeout, cfg.MaxRetries)
	jobProcessor := workers.NewJobProcessor(db, redisClient, apiService)

	// Initialize handlers
	healthHandler := handlers.NewHealthHandler(db, redisClient)
	jobHandler := handlers.NewJobHandler(jobProcessor)

	// Setup Gin router
	if cfg.Environment == "production" {
		gin.SetMode(gin.ReleaseMode)
	}

	router := gin.New()
	router.Use(gin.Logger())
	router.Use(gin.Recovery())

	// Add CORS middleware for development
	if cfg.Environment == "development" {
		router.Use(func(c *gin.Context) {
			c.Header("Access-Control-Allow-Origin", "*")
			c.Header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
			c.Header("Access-Control-Allow-Headers", "Content-Type, Authorization")
			
			if c.Request.Method == "OPTIONS" {
				c.AbortWithStatus(http.StatusOK)
				return
			}
			
			c.Next()
		})
	}

	// Health check endpoints
	router.GET("/health", healthHandler.Check)
	router.GET("/ready", healthHandler.Ready)

	// API routes
	v1 := router.Group("/api/v1")
	{
		v1.POST("/jobs/process", jobHandler.ProcessJob)
		v1.GET("/jobs/:id/status", jobHandler.GetJobStatus)
	}

	// Root endpoint
	router.GET("/", func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{
			"message": "Go Worker Service is running",
			"version": "1.0.0",
			"health":  "/health",
		})
	})

	// Start server
	srv := &http.Server{
		Addr:    ":" + cfg.Port,
		Handler: router,
	}

	// Graceful shutdown
	go func() {
		if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			logger.Error().Err(err).Msg("Failed to start server")
			os.Exit(1)
		}
	}()

	logger.Info().Str("port", cfg.Port).Msg("Server started successfully")

	// Wait for interrupt signal
	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
	<-quit

	logger.Info().Msg("Shutting down server...")

	// Graceful shutdown with timeout
	ctx, cancel = context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()

	if err := srv.Shutdown(ctx); err != nil {
		logger.Error().Err(err).Msg("Server forced to shutdown")
		os.Exit(1)
	}

	logger.Info().Msg("Server exited successfully")
}