package src

import (
	"os"
	"strconv"
)

type Config struct {
	API struct {
		Port int
	}

	GitHub struct {
		BaseURL  string
		Username string
		Token    string
	}
	JIRA struct {
		BaseURL  string
		Username string
		Password string
	}
}

// NewConfig is a constructor that loads environment variables from the
// environment and does minor manipulation of the values.
func NewConfig() (*Config, error) {
	p := os.Getenv("PORT")
	port, err := strconv.Atoi(p)
	if err != nil {
		return nil, err
	}

	return &Config{
		API: struct{ Port int }{port},
		GitHub: struct {
			BaseURL  string
			Username string
			Token    string
		}{},
		JIRA: struct {
			BaseURL  string
			Username string
			Password string
		}{},
	}, nil
}
