package tempo

import (
	"bytes"
	"encoding/json"
	"errors"
	"fmt"
	"io/ioutil"
	"log"
	"net/http"

	jira "gopkg.in/andygrunwald/go-jira.v1"
)

type Client struct {
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
		workLogURL: fmt.Sprintf("https://%s/rest/tempo-timesheets/4/worklogs", baseURL),
		client:     c,
	}
}

func (t *Client) GetLogs(q *Query) ([]Worklog, error) {
	var logs []Worklog
	bod, _ := json.Marshal(q)
	res, err := t.client.Post(t.workLogURL+"/search", "application/json", bytes.NewBuffer(bod))
	if err != nil {
		log.Printf("%v: %+v", q.From, err)
		return logs, err
	}
	defer res.Body.Close()

	if res.StatusCode >= 300 {
		b, err := ioutil.ReadAll(res.Body)
		if err != nil {
			return logs, err
		}
		return logs, errors.New(string(b))
	}

	if err := json.NewDecoder(res.Body).Decode(&logs); err != nil {
		return logs, err
	}

	return logs, nil
}

func (t *Client) CreateLog(wl *Worklog) error {
	bod, _ := json.Marshal(wl)

	res, err := t.client.Post(t.workLogURL, "application/json", bytes.NewBuffer(bod))
	if err != nil {
		log.Printf("%v: %+v", wl.Started, err)
		return err
	}
	defer res.Body.Close()

	if res.StatusCode >= 300 {
		b, err := ioutil.ReadAll(res.Body)
		if err != nil {
			return err
		}
		return errors.New(string(b))
	}

	log.Println("logging time")
	return nil
}

func (t *Client) DeleteLog(w *Worklog) error {
	log.Println("preparing to delete", w)
	if w.TempoWorklogId == 0 {
		return nil
	}
	url := fmt.Sprintf("%s/%d", t.workLogURL, w.TempoWorklogId)
	req, _ := http.NewRequest(http.MethodDelete, url, nil)

	res, err := t.client.Do(req)
	if err != nil {
		log.Printf("%v: %+v", w.Started, err)
		return err
	}
	defer res.Body.Close()

	if res.StatusCode >= 300 {
		b, err := ioutil.ReadAll(res.Body)
		if err != nil {
			return err
		}
		return fmt.Errorf("%s: %s", res.Status, string(b))
	}

	return nil
}
