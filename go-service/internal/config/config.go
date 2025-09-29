package config

import (
	"os"
	"strconv"
)

type Config struct {
	// Server
	Port string

	// Database
	DatabaseURL string

	// Redis
	RedisURL string

	// Logging
	LogLevel string

	// Environment
	Environment string

	// External API settings
	HTTPTimeout int
	MaxRetries  int
}

func Load() *Config {
	return &Config{
		Port:        getEnv("PORT", "8080"),
		DatabaseURL: getEnv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/appdb"),
		RedisURL:    getEnv("REDIS_URL", "redis://localhost:6379/0"),
		LogLevel:    getEnv("LOG_LEVEL", "info"),
		Environment: getEnv("ENVIRONMENT", "development"),
		HTTPTimeout: getEnvAsInt("HTTP_TIMEOUT", 30),
		MaxRetries:  getEnvAsInt("MAX_RETRIES", 3),
	}
}

func getEnv(key, defaultValue string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return defaultValue
}

func getEnvAsInt(key string, defaultValue int) int {
	if value := os.Getenv(key); value != "" {
		if intValue, err := strconv.Atoi(value); err == nil {
			return intValue
		}
	}
	return defaultValue
}
