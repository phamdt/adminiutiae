package controllers

import (
	"encoding/base64"
	"fmt"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/stretchr/testify/assert"

	"github.com/DATA-DOG/go-sqlmock"
	"github.com/jmoiron/sqlx"
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
			name:           "Test creating with valid Code as body",
			authorization:  fmt.Sprintf("Basic: %s", yaaBasic("user:api_key")),
			path:           "/github/SD/code/counts",
			wantStatusCode: http.StatusOK,
		},
		{
			name:           "Test creating with empty request body",
			authorization:  fmt.Sprintf("Basic: %s", yaaBasic("user:api_key")),
			path:           "/github/SD/code/counts",
			wantStatusCode: http.StatusBadRequest,
		},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			router := GetRouter(sqlxDB)

			w := httptest.NewRecorder()
			req, _ := http.NewRequest("POST", tt.path, nil)
			router.ServeHTTP(w, req)

			assert.Equal(t, tt.wantStatusCode, w.Code, w.Body)
		})
	}
}

func yaaBasic(credentials string) string {
	return base64.StdEncoding.EncodeToString([]byte(credentials))
}
