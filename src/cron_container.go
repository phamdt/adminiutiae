package src

import "github.com/phamdt/adminiutiae/src/service"

type CronContainer struct {
	CheckTempo func()
}

func NewCronContainer(c *Config) *CronContainer {
	admBaseURL := "http://localhost:8484/teams/210/worklogs"
	worklogService := service.NewWorklogService(admBaseURL)
	return &CronContainer{
		CheckTempo: worklogService.CheckTempo,
	}
}
