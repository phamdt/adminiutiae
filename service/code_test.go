package service

import (
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
