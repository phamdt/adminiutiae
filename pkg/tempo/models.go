package tempo

type Worklog struct {
	TempoWorklogId   int    `json:"tempoWorklogId,omitempty"`
	Comment          string `json:"comment,omitempty"`
	Started          string `json:"started,omitempty"`
	TimeSpentSeconds int    `json:"timeSpentSeconds,omitempty"`
	Worker           string `json:"worker,omitempty"`
	OriginTaskID     int    `json:"originTaskId,omitempty"`
}

type Query struct {
	Worker []string `json:"worker,omitempty"`
	To     string   `json:"to,omitempty"`   // a date time
	From   string   `json:"from,omitempty"` // a date time
}
