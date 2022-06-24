package tempo

import (
	"encoding/json"
	"errors"
	"fmt"
	"io/ioutil"
	"log"

	e "github.com/pkg/errors"
	null "gopkg.in/guregu/null.v2"
)

type MemberResponse struct {
	ID     int `json:"id"`
	Member struct {
		ActiveInJira bool        `json:"activeInJira"`
		Avatar       null.String `json:"avatar"`
		DisplayName  string      `json:"displayName"`
		Key          string      `json:"key"`
		Message      string      `json:"message"`
		Name         string      `json:"name"`
		Type         string      `json:"type"`
	} `json:"member"`
	Membership struct {
		Availability string `json:"availability"`
		DateFrom     string `json:"dateFrom"`
		DateFromANSI string `json:"dateFromANSI"`
		DateTo       string `json:"dateTo"`
		DateToANSI   string `json:"dateToANSI"`
		ID           int    `json:"id"`
		Role         struct {
			Default bool   `json:"default"`
			ID      int    `json:"id"`
			Name    string `json:"name"`
		} `json:"role"`
		Status       string `json:"status"`
		TeamID       int    `json:"teamId"`
		TeamMemberID int    `json:"teamMemberId"`
	} `json:"membership"`
}

func (t *Client) GetMembers(teamID int) ([]MemberResponse, error) {
	var mr []MemberResponse

	requestURL := fmt.Sprintf(t.teamURL+"/%d/member", teamID)
	log.Println("preparing to request", requestURL)
	res, err := t.client.Get(requestURL)
	if err != nil {
		log.Println("err request member info", err.Error())
		return mr, e.Wrap(err, "http request")
	}
	defer res.Body.Close()

	if res.StatusCode >= 300 {
		b, err := ioutil.ReadAll(res.Body)
		if err != nil {
			log.Println("err non success", err.Error())
			return mr, err
		}
		return mr, errors.New(string(b))
	}

	if err := json.NewDecoder(res.Body).Decode(&mr); err != nil {
		log.Println("err decoding", err.Error())
		return mr, err
	}

	return mr, nil
}
