package src

import (
	"context"
	"fmt"
	"log"
	"net/http"
	"time"

	"github.com/gin-gonic/gin"
)

// Application is our definition of what this API is, the combination of
// an app specific configuration, a router with routes, a container of
// go objects, and a server configured to use the router.
type Application struct {
	config    *Config
	router    *gin.Engine
	container *Container
	server    *http.Server
	Cleanup   func()
}

// NewApplication is a constructor for Application which can
// be used in various commands e.g. api, test, cli, etc.
func NewApplication(c *Config) (*Application, error) {
	container, cleanup, err := NewContainer(c)
	if err != nil {
		return nil, err
	}

	router, err := NewRouter(container)
	if err != nil {
		return nil, err
	}

	var srv http.Server
	srv.Handler = router
	srv.Addr = fmt.Sprintf(":%d", c.API.Port)

	return &Application{
		config:    c,
		router:    router,
		container: container,
		server:    &srv,
		Cleanup:   cleanup,
	}, nil
}

// Start serves the API
func (a *Application) Start() {
	log.Println("starting application server")
	if err := a.server.ListenAndServe(); err != http.ErrServerClosed {
		log.Fatalf("api server closed: %v", err)
		a.Cleanup()
	}
}

// Stop shuts down the API
func (a *Application) Stop(ctx *context.Context) error {
	defer a.Cleanup()

	// The context is used to inform the server it has 5 seconds to finish
	// the request it is currently handling. You might want to make this a
	// configurable property
	tctx, cancel := context.WithTimeout(*ctx, 5*time.Second)
	defer cancel()

	log.Println("shutting down application")
	if err := a.server.Shutdown(tctx); err != nil {
		return err
	}

	return nil
}

// GetRouter is mostly for testing but allows retrieving the router
func (a *Application) GetRouter() *gin.Engine {
	return a.router
}
