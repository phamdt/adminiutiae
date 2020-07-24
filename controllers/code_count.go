package controllers

import (
	"bytes"
	"context"
	"encoding/base64"
	"encoding/csv"
	"fmt"
	"log"
	"net/http"
	"os"
	"strings"

	"github.com/gin-gonic/gin"
	"github.com/phamdt/adminiutiae/service"
	"github.com/pkg/errors"
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

	// TODO: move auth to middleware
	h := c.GetHeader("Authorization")
	user, token, err := GetBasicCredentials(h)
	if err != nil {
		log.Printf("Error creating code count report: %+v", err)
		c.AbortWithStatus(http.StatusUnauthorized)
		return
	}

	user = strings.ToLower(user)
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
	b := &bytes.Buffer{}
	writer := csv.NewWriter(b)
	defer writer.Flush()

	writer.Write(header)
	writer.WriteAll(rows)

	c.Header("Content-Description", "File Transfer")
	c.Header("Content-Disposition", "attachment; filename=count_count.csv")
	c.Data(http.StatusCreated, "text/csv", b.Bytes())
}

func GetBasicCredentials(header string) (string, string, error) {
	if header == "" {
		return "", "", errors.New("missing authorization")
	}

	authParts := strings.Split(header, "Basic ")
	if len(authParts) < 1 {
		return "", "", errors.New("missing basic authorization")
	}

	token := authParts[1]
	data, err := base64.StdEncoding.DecodeString(token)
	if err != nil {
		return "", "", err
	}

	parts := strings.Split(string(data), ":")
	return parts[0], parts[1], nil
}
