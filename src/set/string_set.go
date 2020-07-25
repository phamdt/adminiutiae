package set

type StringSet struct {
	index map[string]int
}

func NewStringSet() StringSet {
	i := make(map[string]int)
	return StringSet{
		index: i,
	}
}

func (s *StringSet) List() []string {
	l := make([]string, len(s.index))
	for str, index := range s.index {
		l[index] = str
	}
	return l
}

func (s *StringSet) Add(str string) {
	if _, ok := s.index[str]; !ok {
		index := len(s.index)
		s.index[str] = index
	}
}

func (s *StringSet) Has(str string) bool {
	_, ok := s.index[str]
	return ok
}
