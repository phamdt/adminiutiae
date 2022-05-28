package src

import (
	"context"

	"github.com/phamdt/adminiutiae/src/controllers"
	"github.com/phamdt/adminiutiae/src/service"
)

type Container struct {
	CodeCountController *controllers.CodeCountController
}

// CleanupFunc should wrap all of the resources that must be explicitly closed
// as part of a graceful and complete shutdown. This might be a function that
// ensures idle connections are severed or addressing possible memory leaks.
// If this function encloses multiple operations/functions, it is up to the
// caller to ensure that they are done in the correct order if order matters.
type CleanupFunc func()

func NewContainer(c *Config) (*Container, CleanupFunc, error) {
	cleanup := func() {
	}

	ctx := context.Background()

	codeCountService := service.NewCounter(ctx, c.GitHub.Token, c.GitHub.BaseURL)
	codeCtrl := controllers.NewCodeCountController(&codeCountService)

	return &Container{
		CodeCountController: codeCtrl,
	}, cleanup, nil
}
