package main

import (
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"os"
	"os/signal"
	"strconv"
	"strings"
	"syscall"
	"time"

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
	log.Println("starting cronapp")
	a.cron.Start()
}

func (a *CronApp) Stop() {
	log.Println("stopping cronapp")
	a.cron.Stop()
}

func NewCronApp() (*CronApp, error) {
	c := cron.New(cron.WithLocation(time.UTC),
		cron.WithChain(
			cron.Recover(cron.DefaultLogger),
			cron.SkipIfStillRunning(cron.DefaultLogger),
		))

	return &CronApp{c}, nil
}

func (a *CronApp) RegisterJobs() {
	// every minute
	a.cron.AddFunc("0/1 * * * *", func() {
		c := http.Client{}
		var responseList []map[string]interface{}

		res, err := c.Get("http://localhost:8484/teams/210/worklogs?from=2022-05-15&to=2022-06-15")
		if err != nil {
			log.Println(err.Error())
			return
		}
		defer res.Body.Close()

		// the key is the json property we expect to find the data from the first API response
		// the value is the outgoing request body to the second API
		keyMap := map[string]string{
			"user":  "user.name",
			"hours": "hours",
		}

		// each dynamic http job can have 1 of 2 flows
		// 1 post/put/patch/delete some stored/generated value to some url
		// 2 get a url, extract/transform values,
		// 	post/put/patch/delete to another url with a map/json config so we know how
		// how to turn the result of the first api into the second
		json.NewDecoder(res.Body).Decode(&responseList)
		transformed := []map[string]interface{}{}

		for _, item := range responseList {
			outgoingRequest := map[string]interface{}{}

			for sourceKey, destination := range keyMap {
				keys := strings.Split(destination, ".")

				lastID := len(keys) - 1
				level := map[string]interface{}{}
				for id, key := range keys {
					if lastID == id {
						log.Println(item[sourceKey])
						level[key] = getValue(sourceKey, item)
					} else {
						outgoingRequest[key] = map[string]interface{}{}
						level = outgoingRequest[key].(map[string]interface{})
					}
				}
			}
			transformed = append(transformed, outgoingRequest)
		}
	})
}

func getValue(key string, m map[string]interface{}) string {
	keys := strings.Split(key, ".")
	for _, current := range keys {
		if _, ok := m[current]; !ok {
			return "" // should be err?
		}

		switch m[current].(type) {
		case string:
			return m[current].(string)
		case map[string]interface{}:
			m = m[current].(map[string]interface{})
		case int, int64:
			i := m[current].(int)
			return strconv.Itoa(i)
		case float32, float64:
			f := m[current].(float64)
			return fmt.Sprintf("%f", f)
		default:
			log.Println("Wat is this")
		}
	}

	return ""
}

func printJSON(name string, i interface{}) {
	f, _ := os.Create(name)
	defer f.Close()

	b, _ := json.Marshal(i)
	f.Write(b)
}
