package controllers

import (
	"context"
	"encoding/base64"
	"encoding/csv"
	"fmt"
	"log"
	"net/http"
	"os"
	"strings"

	"github.com/gin-gonic/gin"
	"github.com/jmoiron/sqlx"
	"github.com/phamdt/adminiutiae/service"
	"github.com/pkg/errors"
)

// CodeCountController exposes the methods for interacting with the
// RESTful CodeCount resource
type CodeCountController struct {
	db      *sqlx.DB
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

	newCsv, err := os.Create("code_count.csv")
	if err != nil {
		c.AbortWithError(http.StatusInternalServerError, err)
		return
	}
	defer newCsv.Close()

	writer := csv.NewWriter(newCsv)
	defer writer.Flush()

	writer.Write(header)
	writer.WriteAll(rows)
	c.JSON(http.StatusCreated, gin.H{})
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
