package middleware

import (
	"encoding/base64"
	"fmt"
	"testing"
)

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

func yaaBasic(credentials string) string {
	encoded := base64.StdEncoding.EncodeToString([]byte(credentials))
	return fmt.Sprintf("Basic %s", encoded)
}
