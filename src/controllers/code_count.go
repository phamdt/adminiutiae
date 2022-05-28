package controllers

import (
	"net/http"

	"github.com/gin-gonic/gin"
	"github.com/phamdt/adminiutiae/src/response"
)

// CodeCountController exposes the methods for interacting with the
// RESTful CodeCount resource
type CodeCountController struct {
	counter ICounter
}

type ICounter interface {
	GetGithubLOC(string, string) ([]string, [][]string, error)
}

func NewCodeCountController(c ICounter) *CodeCountController {
	return &CodeCountController{c}
}

// Create generates a code count report to be returned to the user
func (ctrl *CodeCountController) Create(c *gin.Context) {
	outputBaseDir := "/tmp/github"

	org := c.Param("org")
	header, rows, err := ctrl.counter.GetGithubLOC(outputBaseDir, org)
	if err != nil {
		c.AbortWithError(http.StatusInternalServerError, err)
		return
	}

	// TODO: toggle content type

	c.Header("Content-Description", "File Transfer")
	c.Header("Content-Disposition", "attachment; filename=count_count.csv")
	c.Data(http.StatusCreated, "text/csv", response.ToCSV(header, rows))
}
