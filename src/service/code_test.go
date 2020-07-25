package service

import (
	"context"
	"testing"
)

func TestCounter_GetGithubLOC(t *testing.T) {
	type fields struct {
		Token      string
		BaseGitURL string
	}
	type args struct {
		outputBaseDir string
		org           string
	}
	tests := []struct {
		name    string
		fields  fields
		args    args
		wantErr bool
	}{
		{
			name: "test counting org repos code count happy path",
			fields: fields{
				Token:      "{add your token here temporarily}",
				BaseGitURL: "https://github.com",
			},
			args: args{
				outputBaseDir: "/tmp/somename",
				org:           "githuborgoruser",
			},
		},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			c := NewCounter(context.Background(), tt.fields.Token, tt.fields.BaseGitURL)
			headers, rows, err := c.GetGithubLOC(tt.args.outputBaseDir, tt.args.org)
			if (err != nil) != tt.wantErr {
				t.Errorf("Counter.GetGithubLOC() error = %v, wantErr %v", err, tt.wantErr)
				return
			}

			if len(headers) <= 3 {
				t.Error("Expected more than the default headers")
			}
			if len(headers) != len(rows[0]) {
				t.Errorf("Expected header length %d to equal row length %d", len(headers), len(rows[0]))
			}
		})
	}
}
