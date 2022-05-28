package middleware

import (
	"encoding/base64"
	"errors"
	"log"
	"net/http"
	"strings"

	"github.com/gin-gonic/gin"
	"github.com/phamdt/adminiutiae/src/controllers/context"
)

func HasBasicAuth(c *gin.Context) {
	h := c.GetHeader("Authorization")
	user, token, err := GetBasicCredentials(h)
	if err != nil {
		log.Printf("Error creating code count report: %+v", err)
		c.AbortWithStatus(http.StatusUnauthorized)
		return
	}

	user = strings.ToLower(user)
	c.Set(context.UserKey, user)
	c.Set(context.TokenKey, token)
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
