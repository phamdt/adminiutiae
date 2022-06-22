package tempo

type Worklog struct {
	TempoWorklogId   int    `json:"tempoWorklogId,omitempty"`
	Comment          string `json:"comment,omitempty"`
	Started          string `json:"started,omitempty"`
	TimeSpentSeconds int    `json:"timeSpentSeconds,omitempty"`
	Worker           string `json:"worker,omitempty"`
	OriginTaskID     int    `json:"originTaskId,omitempty"`
	Issue            Issue  `json:"issue,omitempty"`
}

type Issue struct {
	AccountKey string `json:"accountKey,omitempty"`
	Key        string `json:"key,omitempty"`
	Summary    string `json:"summary,omitempty"`
}

type FindRequest struct {
	AccountID       []int    `json:"accountId,omitempty"`
	AccountKey      []string `json:"accountKey,omitempty"`
	CategoryID      []int    `json:"categoryId,omitempty"`
	CategoryTypeID  []int    `json:"categoryTypeId,omitempty"`
	CustomerID      []int    `json:"customerId,omitempty"`
	EpicKey         []string `json:"epic_key,omitempty"` // ex. "PROJ-1234"
	From            string   `json:"from,omitempty"`     // ex. "yyyy-MM-dd"
	Include         []string `json:"include,omitempty"`  // ex. "ISSUE"
	IncludeSubtasks bool     `json:"include_subtasks,omitempty"`
	LocationID      []int    `json:"locationId,omitempty"`
	ProjectID       []int    `json:"projectId,omitempty"`
	ProjectKey      []string `json:"project_key,omitempty"` // ex. "PROJ"
	RoleID          []int    `json:"roleId,omitempty"`
	TaskID          []int    `json:"taskId,omitempty"`
	TaskKey         []string `json:"task_key,omitempty"` // ex. "PROJ-1234"
	TeamID          []int    `json:"teamId,omitempty"`
	To              string   `json:"to,omitempty"` // ex. "yyyy-MM-dd"
	Worker          []string `json:"worker,omitempty"`
}

type FindResponse []struct {
	Attributes      map[string]interface{} `json:"attributes"`
	BillableSeconds int                    `json:"billableSeconds"`
	Comment         string                 `json:"comment"`
	Created         string                 `json:"created"`
	ID              int                    `json:"id"`
	Issue           struct {
		AccountKey    string `json:"accountKey"`
		IconURL       string `json:"iconUrl"`
		ID            int    `json:"id"`
		InternalIssue bool   `json:"internalIssue"`
		IssueStatus   string `json:"issueStatus"`
		IssueType     string `json:"issueType"`
		Key           string `json:"key"`
		ParentIssue   struct {
			IconURL   string `json:"iconUrl"`
			IssueType string `json:"issueType"`
			Summary   string `json:"summary"`
		} `json:"parentIssue"`
		ParentKey   string `json:"parentKey"`
		ProjectID   int    `json:"projectId"`
		ProjectKey  string `json:"projectKey"`
		ReporterKey string `json:"reporterKey"`
		Summary     string `json:"summary"`
	} `json:"issue"`
	IssueID       int `json:"issueId"`
	JiraWorklogID int `json:"jiraWorklogId"`
	Location      struct {
		ID   int    `json:"id"`
		Name string `json:"name"`
	} `json:"location"`
	StartDate        string `json:"startDate"`
	TempoWorklogID   int    `json:"tempoWorklogId"`
	TimeSpentSeconds int    `json:"timeSpentSeconds"`
	Updated          string `json:"updated"`
	UpdaterKey       string `json:"updaterKey"`
	WorkerKey        string `json:"workerKey"`
}

type UpdateRequest struct {
	Attributes            map[string]interface{} `json:"attributes"`
	BillableSeconds       int                    `json:"billableSeconds"`
	Comment               string                 `json:"comment"`
	EndDate               string                 `json:"endDate"`
	IncludeNonWorkingDays bool                   `json:"includeNonWorkingDays"`
	RemainingEstimate     int                    `json:"remainingEstimate"`
	Started               string                 `json:"started"`
	TimeSpentSeconds      int                    `json:"timeSpentSeconds"`
}
