package main

import (
	"context"
	"log"
	"os"
	"os/signal"
	"syscall"

	app "github.com/phamdt/adminiutiae/src"
)

// main is the go required function name for any package that can be executed.
func main() {
	c, err := app.NewConfig()
	if err != nil {
		log.Fatal(err)
	}

	ctx := context.Background()

	a, err := app.NewApplication(c)
	if err != nil {
		log.Fatal(err)
	}

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
		a.Stop(&ctx)

		// we close the 'run' channel thus exiting the main function
		// and therefore the app.
		close(run)
	}()

	a.Start()
	<-run
}
