package main

import (
	"log"
	"os"
	"os/signal"
	"syscall"

	"github.com/phamdt/adminiutiae/src"
)

func main() {
	c, err := src.NewConfig()
	if err != nil {
		log.Fatal(err)
	}

	a, err := src.NewCronApp(c)
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
