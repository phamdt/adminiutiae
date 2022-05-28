package service

import (
	"errors"
	"strconv"

	"github.com/phamdt/adminiutiae/pkg/set"
)

// LanguageSummary is derived from bcc's processor.LanguageSummary
type LanguageSummary struct {
	Name               string
	Bytes              int64
	Lines              int64
	Code               int64
	Comment            int64
	Blank              int64
	Complexity         int64
	Count              int64
	WeightedComplexity float64
}

type SummarySet struct {
	index map[string]SummaryMeta
}

func NewSummarySet() SummarySet {
	return SummarySet{
		index: make(map[string]SummaryMeta),
	}
}

func (s *SummarySet) Add(sum LanguageSummary) {
	if _, ok := s.index[sum.Name]; !ok {
		index := len(s.index)
		s.index[sum.Name] = SummaryMeta{
			Index: index,
			Code:  sum.Code,
		}
	}
}

func (s *SummarySet) Has(str string) bool {
	_, ok := s.index[str]
	return ok
}

func (s *SummarySet) GetSummaryMeta(name string) (SummaryMeta, error) {
	if s.Has(name) {
		return s.index[name], nil
	}
	return SummaryMeta{}, errors.New("not found")
}

type SummaryMeta struct {
	Code  int64
	Index int
}

func ExtractLanguageCounts(languageSet *set.StringSet, summaries []LanguageSummary) []string {
	localSet := NewSummarySet()
	for _, languageSummary := range summaries {
		// update global language lookup
		languageSet.Add(languageSummary.Name)
		// update file specific lookup
		localSet.Add(languageSummary)
	}

	counts := []string{}
	for _, language := range languageSet.List() {
		// if localset has the language
		if localSet.Has(language) {
			// add the count
			s, err := localSet.GetSummaryMeta(language)
			if err != nil {
				panic(err)
			}
			count := strconv.FormatInt(s.Code, 10)
			counts = append(counts, count)
		} else {
			// add empty string
			counts = append(counts, "")
		}
	}
	return counts
}
