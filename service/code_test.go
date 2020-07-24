package service

import (
	"context"
	"reflect"
	"testing"

	"github.com/boyter/scc/processor"
	"github.com/phamdt/adminiutiae/set"
)

func TestExtractLanguageCounts(t *testing.T) {
	type args struct {
		languageSet set.StringSet
		summaries   []processor.LanguageSummary
	}
	tests := []struct {
		name string
		args args
		want []string
	}{
		{
			name: "extract languages from one file",
			args: args{
				languageSet: set.NewStringSet(),
				summaries: []processor.LanguageSummary{
					{
						Name:  "JS",
						Count: 1,
					},
					{
						Name:  "Go",
						Count: 2,
					},
				},
			},
			want: []string{"1", "2"},
		},
		{
			name: "extract languages from second file with different languages",
			args: args{
				languageSet: differentLanguages(),
				summaries: []processor.LanguageSummary{
					{
						Name:  "JS",
						Count: 1,
					},
					{
						Name:  "Go",
						Count: 2,
					},
				},
			},
			want: []string{"", "", "1", "2"},
		},
		{
			name: "extract languages from second file with intersecting languages",
			args: args{
				languageSet: differentLanguages(),
				summaries: []processor.LanguageSummary{
					{
						Name:  "Perl",
						Count: 1,
					},
					{
						Name:  "Go",
						Count: 2,
					},
				},
			},
			want: []string{"1", "", "2"},
		},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			if got := ExtractLanguageCounts(tt.args.languageSet, tt.args.summaries); !reflect.DeepEqual(got, tt.want) {
				t.Errorf("ExtractLanguageCounts() = %+v, want %+v", got, tt.want)
			}
		})
	}
}

func differentLanguages() set.StringSet {
	s := set.NewStringSet()
	s.Add("Perl")
	s.Add("Rust")
	return s
}

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
