package tempo

import (
	"fmt"
	"net/http"

	jira "gopkg.in/andygrunwald/go-jira.v1"
)

type Client struct {
	teamURL    string
	workLogURL string
	client     *http.Client
}

func NewClient(baseURL, username, password string) *Client {
	t := jira.BasicAuthTransport{
		Username: username,
		Password: password,
	}
	c := t.Client()

	return &Client{
		teamURL:    fmt.Sprintf("https://%s/rest/tempo-teams/2/team", baseURL),
		workLogURL: fmt.Sprintf("https://%s/rest/tempo-timesheets/4/worklogs", baseURL),
		client:     c,
	}
}
