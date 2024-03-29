package src

import (
	"github.com/gin-gonic/gin"
)

// NewRouter is a constructor to create a new router
// with registered routes
func NewRouter(c *Container) (*gin.Engine, error) {
	// create a router
	r := gin.Default()
	r.RedirectTrailingSlash = true

	// r.Use(middleware.HasBasicAuth)

	RegisterRoutes(c, r)

	return r, nil
}

func RegisterRoutes(co *Container, r *gin.Engine) {
	// Here you can define the HTTP method, the path, and the handler.
	r.POST("/code/count", co.CodeCountController.Create)
	r.GET("/teams/:teamID/members", co.TeamMemberController.Index)
	r.GET("/teams/:teamID/worklogs", co.TeamWorklogsController.Index)
	r.GET("/tickets", co.TicketController.Index)
	r.GET("/tickets/:projectKey", co.TicketController.Show)
}
