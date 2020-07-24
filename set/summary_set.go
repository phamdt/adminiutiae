package set

import (
	"errors"

	"github.com/boyter/scc/processor"
)

type SummarySet struct {
	index map[string]SummaryMeta
}

func NewSummarySet() SummarySet {
	return SummarySet{
		index: make(map[string]SummaryMeta),
	}
}

func (s *SummarySet) Add(sum processor.LanguageSummary) {
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
