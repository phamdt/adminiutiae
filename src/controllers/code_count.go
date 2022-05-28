package controllers

import (
	"context"
	"fmt"
	"net/http"
	"os"

	"github.com/gin-gonic/gin"
	icontext "github.com/phamdt/adminiutiae/src/controllers/context"
	"github.com/phamdt/adminiutiae/src/response"
	"github.com/phamdt/adminiutiae/src/service"
)

// CodeCountController exposes the methods for interacting with the
// RESTful CodeCount resource
type CodeCountController struct {
	counter ICounter
}

type ICounter interface {
	GetGithubLOC(string, string) ([]string, [][]string, error)
}

// Create generates a code count report to be returned to the user
func (ctrl *CodeCountController) Create(c *gin.Context) {
	baseGitURL := os.Getenv("BASE_GIT_URL")

	user := c.GetString(icontext.UserKey)
	token := c.GetString(icontext.TokenKey)
	outputBaseDir := fmt.Sprintf("/tmp/%s", user)
	org := c.Param("org")

	ctx := context.Background()
	if ctrl.counter == nil {
		local := service.NewCounter(ctx, token, baseGitURL)
		ctrl.counter = &local
	}

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
