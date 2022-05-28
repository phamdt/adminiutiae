package src

import (
	"github.com/gin-gonic/gin"
)

// NewRouter is a constructor to create a new router
// with registered routes
func NewRouter(c *Container) (*gin.Engine, error) {
	// create a router
	r := gin.Default()

	RegisterRoutes(c, r)

	return r, nil
}

func RegisterRoutes(c *Container, r *gin.Engine) {
	// Here you can define the HTTP method, the path, and the handler.
	r.POST("/code/count", c.CodeCountController.Create)
}
