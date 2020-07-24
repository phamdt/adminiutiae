package controllers

import (
	"encoding/base64"
	"fmt"
	"net/http"
	"testing"

	"github.com/gin-gonic/gin"
	"github.com/phamdt/adminiutiae/service"
	"github.com/steinfletcher/apitest"
)

func TestCodeCountController_Create(t *testing.T) {
	tests := []struct {
		name           string
		authorization  string
		path           string
		wantStatusCode int
	}{
		{
			name:           "Test missing Basic Auth",
			authorization:  "",
			path:           "/github/org/code/counts",
			wantStatusCode: http.StatusUnauthorized,
		},
		{
			name:           "Test creating csv code count report happy path",
			authorization:  yaaBasic("user:api_key"),
			path:           "/github/org/code/counts",
			wantStatusCode: http.StatusCreated,
		},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			router := gin.Default()
			counter := MockCounter{}
			codeCountCtrl := CodeCountController{counter: &counter}
			router.POST("/github/:org/code/counts", codeCountCtrl.Create)

			apitest.New().
				Handler(router).
				Post(tt.path).
				Headers(map[string]string{"Authorization": tt.authorization}).
				Expect(t).
				Status(tt.wantStatusCode).
				End()
		})
	}
}

type MockCounter struct{}

func (c *MockCounter) GetGithubLOC(dir string, org string) ([]string, [][]string, error) {
	rows := [][]string{[]string{"org", "name", "git url", "1", "", "2"}}
	return service.GetDefaultHeaders(), rows, nil
}

func yaaBasic(credentials string) string {
	encoded := base64.StdEncoding.EncodeToString([]byte(credentials))
	return fmt.Sprintf("Basic %s", encoded)
}

func getRepositoryAPIMock() *apitest.Mock {
	return apitest.NewMock().
		Get("/api/v3/orgs/org/repos?per_page=2").
		RespondWith().
		Body(`
		[{"id": 1, "archived": false, "full_name": "github.com/org/repo1", "clone_url": "fakegithub.example.com/repo.git"}]
		`).
		Status(http.StatusOK).
		End()
}

func TestGetBasicCredentials(t *testing.T) {
	type args struct {
		header string
	}
	tests := []struct {
		name    string
		args    args
		user    string
		token   string
		wantErr bool
	}{
		{
			name: "test decoding well formed authorization header",
			args: args{
				header: yaaBasic("user:api_key"),
			},
			user:    "user",
			token:   "api_key",
			wantErr: false,
		},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got, got1, err := GetBasicCredentials(tt.args.header)
			if (err != nil) != tt.wantErr {
				t.Errorf("GetBasicCredentials() error = %v, wantErr %v", err, tt.wantErr)
				return
			}
			if got != tt.user {
				t.Errorf("GetBasicCredentials() got = %v, want %v", got, tt.user)
			}
			if got1 != tt.token {
				t.Errorf("GetBasicCredentials() got1 = %v, want %v", got1, tt.token)
			}
		})
	}
}
