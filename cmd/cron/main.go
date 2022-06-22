package main

import (
	"log"
	"os"
	"os/signal"
	"syscall"

	"github.com/robfig/cron/v3"
)

func main() {
	a, err := NewCronApp()
	if err != nil {
		log.Fatal(err)
	}

	a.RegisterJobs()

	// signal handling
	run := make(chan struct{})
	go func() {
		signals := make(chan os.Signal, 1)

		// kill (no param) default send syscall.SIGTERM
		// kill -2 is syscall.SIGINT but os.Interrupt is the OS agnostic version
		signal.Notify(signals, os.Interrupt, syscall.SIGTERM)
		<-signals

		// What's happening above? This function will wait for a signal like
		// the one sent from you, the user, hitting CTRL-C. If it receives
		// a signal, it closes the blocking channel, 'signals', then proceeds
		// with the code below.

		// we stop our application and cleanup after ourselves
		a.Stop()

		// we close the 'run' channel thus exiting the main function
		// and therefore the app.
		close(run)
	}()

	a.Start()
	<-run
}

type CronApp struct {
	cron *cron.Cron
}

func (a *CronApp) Start() {
	a.cron.Start()
}

func (a *CronApp) Stop() {
	a.cron.Stop()
}

func NewCronApp() (*CronApp, error) {
	c := cron.New(cron.WithChain(
		cron.Recover(cron.DefaultLogger),
	))

	return &CronApp{c}, nil
}

func (a *CronApp) RegisterJobs() {
	// every minute
	a.cron.AddFunc("0/1 * * * *", func() {
		log.Println("this works")
	})
}
