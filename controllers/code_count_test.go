package controllers

import (
	"encoding/base64"
	"fmt"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/DATA-DOG/go-sqlmock"
	"github.com/jmoiron/sqlx"
	"github.com/stretchr/testify/assert"
)

func TestCodeCountController_Create(t *testing.T) {
	db, mock, err := sqlmock.New()
	if err != nil {
		t.Fatalf("an error '%s' was not expected when opening a stub database connection: %s", err, mock)
	}
	defer db.Close()
	sqlxDB := sqlx.NewDb(db, "sqlmock")

	tests := []struct {
		name           string
		authorization  string
		path           string
		wantStatusCode int
	}{
		{
			name:           "Test missing Basic Auth",
			authorization:  "",
			path:           "/github/SD/code/counts",
			wantStatusCode: http.StatusUnauthorized,
		},
		{
			name:           "Test creating csv code count report happy path",
			authorization:  yaaBasic("user:api_key"),
			path:           "/github/SD/code/counts",
			wantStatusCode: http.StatusOK,
		},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			router := GetRouter(sqlxDB)

			w := httptest.NewRecorder()
			req, _ := http.NewRequest("POST", tt.path, nil)
			req.Header["Authorization"] = []string{tt.authorization}
			router.ServeHTTP(w, req)

			assert.Equal(t, tt.wantStatusCode, w.Code, w.Body)
		})
	}
}

func yaaBasic(credentials string) string {
	encoded := base64.StdEncoding.EncodeToString([]byte(credentials))
	return fmt.Sprintf("Basic %s", encoded)
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
