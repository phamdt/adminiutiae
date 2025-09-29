package logger

import (
	"os"
	"strings"

	"github.com/rs/zerolog"
	"github.com/rs/zerolog/log"
)

func Init(level string) {
	// Configure zerolog
	zerolog.TimeFieldFormat = zerolog.TimeFormatUnix

	// Set log level
	switch strings.ToLower(level) {
	case "debug":
		zerolog.SetGlobalLevel(zerolog.DebugLevel)
	case "info":
		zerolog.SetGlobalLevel(zerolog.InfoLevel)
	case "warn":
		zerolog.SetGlobalLevel(zerolog.WarnLevel)
	case "error":
		zerolog.SetGlobalLevel(zerolog.ErrorLevel)
	default:
		zerolog.SetGlobalLevel(zerolog.InfoLevel)
	}

	// Pretty print in development
	if os.Getenv("ENVIRONMENT") == "development" {
		log.Logger = log.Output(zerolog.ConsoleWriter{Out: os.Stderr})
	}
}

func Info() *zerolog.Event {
	return log.Info()
}

func Error() *zerolog.Event {
	return log.Error()
}

func Debug() *zerolog.Event {
	return log.Debug()
}

func Warn() *zerolog.Event {
	return log.Warn()
}

func With() zerolog.Context {
	return log.With()
}
