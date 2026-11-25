package controllers

import (
	"fmt"
	"net/http"

	"github.com/gin-gonic/gin"
	jira "gopkg.in/andygrunwald/go-jira.v1"
)

// TicketController exposes methods for listing JIRA tickets.
type TicketController struct {
	jira *jira.Client
}

func NewTicketController(jiraClient *jira.Client) *TicketController {
	return &TicketController{jira: jiraClient}
}

func (ctrl *TicketController) Index(c *gin.Context) {
	list, err := searchAllIssues(ctrl.jira, "")
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, list)
}

func (ctrl *TicketController) Show(c *gin.Context) {
	projectKey := c.Param("projectKey")
	jql := fmt.Sprintf(`project = "%s"`, projectKey)
	list, err := searchAllIssues(ctrl.jira, jql)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, list)
}

func searchAllIssues(client *jira.Client, jql string) ([]jira.Issue, error) {
	var list []jira.Issue
	err := client.Issue.SearchPages(jql, nil, func(issue jira.Issue) error {
		list = append(list, issue)
		return nil
	})
	return list, err
}