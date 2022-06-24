package tempo

import (
	"bytes"
	"encoding/json"
	"errors"
	"fmt"
	"io/ioutil"
	"net/http"
)

func (t *Client) GetLogs(r *FindRequest) ([]Worklog, error) {
	var logs []Worklog
	bod, _ := json.Marshal(r)
	res, err := t.client.Post(t.workLogURL+"/search", "application/json", bytes.NewBuffer(bod))
	if err != nil {
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

	return nil
}

func (t *Client) DeleteLog(w *Worklog) error {
	if w.TempoWorklogId == 0 {
		return nil
	}

	url := fmt.Sprintf("%s/%d", t.workLogURL, w.TempoWorklogId)
	req, _ := http.NewRequest(http.MethodDelete, url, nil)

	res, err := t.client.Do(req)
	if err != nil {
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
