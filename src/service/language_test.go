package service

import (
	"reflect"
	"testing"

	"github.com/phamdt/adminiutiae/pkg/set"
)

func TestExtractLanguageCounts(t *testing.T) {
	type args struct {
		languageSet *set.StringSet
		summaries   []LanguageSummary
	}
	tests := []struct {
		name string
		args args
		want []string
	}{
		{
			name: "extract languages from one new file",
			args: args{
				languageSet: emptySet(),
				summaries: []LanguageSummary{
					{
						Name: "JS",
						Code: 1,
					},
					{
						Name: "Go",
						Code: 2,
					},
				},
			},
			want: []string{"1", "2"},
		},
		{
			name: "extract languages from second file with different languages",
			args: args{
				languageSet: differentLanguages(),
				summaries: []LanguageSummary{
					{
						Name: "JS",
						Code: 1,
					},
					{
						Name: "Go",
						Code: 2,
					},
				},
			},
			want: []string{"", "", "1", "2"},
		},
		{
			name: "extract languages from second file with intersecting languages",
			args: args{
				languageSet: differentLanguages(),
				summaries: []LanguageSummary{
					{
						Name: "Perl",
						Code: 1,
					},
					{
						Name: "Go",
						Code: 2,
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

func emptySet() *set.StringSet {
	s := set.NewStringSet()
	return &s
}

func differentLanguages() *set.StringSet {
	s := set.NewStringSet()
	s.Add("Perl")
	s.Add("Rust")
	return &s
}
