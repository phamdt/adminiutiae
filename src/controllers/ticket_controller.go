package controllers

import (
	"net/http"

	"github.com/gin-gonic/gin"
	jira "gopkg.in/andygrunwald/go-jira.v1"
)

// TicketController exposes methods for listing JIRA tickets.
type TicketController struct {
	jira *jira.Client
}

func NewTicketController(jira *jira.Client) *TicketController {
	return &TicketController{jira: jira}
}

func (ctrl *TicketController) Index(c *gin.Context) {
	list, _, err := ctrl.jira.Issue.Search("", nil)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, list)
}

func (ctrl *TicketController) Show(c *gin.Context) {
	projectKey := c.Param("projectKey")
	jql := "project = " + projectKey
	list, _, err := ctrl.jira.Issue.Search(jql, nil)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, list)
}