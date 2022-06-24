package src

import (
	"log"
	"time"

	cron "github.com/robfig/cron/v3"
)

type CronApp struct {
	cron      *cron.Cron
	container *CronContainer
}

func NewCronApp(config *Config) (*CronApp, error) {
	c := cron.New(cron.WithLocation(time.UTC),
		cron.WithChain(
			cron.Recover(cron.DefaultLogger),
			cron.SkipIfStillRunning(cron.DefaultLogger),
		))

	container := NewCronContainer(config)
	return &CronApp{cron: c, container: container}, nil
}

func (a *CronApp) Start() {
	log.Println("starting cronapp")
	a.cron.Start()
}

func (a *CronApp) Stop() {
	log.Println("stopping cronapp")
	a.cron.Stop()
}

func (a *CronApp) RegisterJobs() {
	// every minute
	a.cron.AddFunc("0/1 * * * *", a.container.CheckTempo)
}
