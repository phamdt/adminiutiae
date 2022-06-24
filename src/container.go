package src

import (
	"context"
	"net/http"

	"github.com/phamdt/adminiutiae/pkg/tempo"
	"github.com/phamdt/adminiutiae/src/controllers"
	"github.com/phamdt/adminiutiae/src/service"
	"gopkg.in/andygrunwald/go-jira.v1"
)

type Container struct {
	Config                 *Config
	JiraClient             *jira.Client
	CodeCountController    *controllers.CodeCountController
	TicketController       *controllers.TicketController
	TeamMemberController   *controllers.TeamController
	TeamWorklogsController *controllers.TeamWorklogsController
}

// CleanupFunc should wrap all of the resources that must be explicitly closed
// as part of a graceful and complete shutdown. This might be a function that
// ensures idle connections are severed or addressing possible memory leaks.
// If this function encloses multiple operations/functions, it is up to the
// caller to ensure that they are done in the correct order if order matters.
type CleanupFunc func()

func NewContainer(c *Config) (*Container, CleanupFunc, error) {
	cleanup := func() {
	}

	ctx := context.Background()

	codeCountService := service.NewCounter(ctx, c.GitHub.Token, c.GitHub.BaseURL)
	tempo := tempo.NewClient(c.Tempo.BaseURL, c.JIRA.Username, c.JIRA.Password)
	hc := http.Client{
		Transport: &jira.BasicAuthTransport{Username: c.JIRA.Username, Password: c.JIRA.Password},
	}
	jiraClient, _ := jira.NewClient(&hc, c.JIRA.BaseURL)
	codeCtrl := controllers.NewCodeCountController(&codeCountService)
	teamMemberCtrl := controllers.NewTeamMemberController(tempo)
	teamWorklogCtrl := controllers.NewTeamWorklogsController(tempo)
	ticketsCtrl := controllers.NewTicketController(jiraClient)

	return &Container{
		Config:                 c,
		JiraClient:             jiraClient,
		CodeCountController:    codeCtrl,
		TeamMemberController:   teamMemberCtrl,
		TeamWorklogsController: teamWorklogCtrl,
		TicketController:       ticketsCtrl,
	}, cleanup, nil
}
