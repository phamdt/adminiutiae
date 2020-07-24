package file

import (
	"fmt"
	"io/ioutil"
	"os"

	"github.com/pkg/errors"
)

func CreateDir(dir string) error {
	if DirExists(dir) {
		if err := os.MkdirAll(dir, os.ModePerm); err != nil {
			return fmt.Errorf(dir, err)
		}
		return nil
	}
	return nil
}

func DirExists(path string) bool {
	_, err := os.Stat(path)
	return !os.IsNotExist(err)
}

// IterateDirectory is a mapping function that iterates through the files of
// the directory then executes the function argument against the file
func IterateDirectory(dir string, f func(string) error) error {
	files, err := ioutil.ReadDir(dir)
	if err != nil {
		return errors.WithStack(err)
	}
	for _, file := range files {
		if err := f(file.Name()); err != nil {
			return errors.WithStack(err)
		}
	}
	return nil
}

func GetFileBytes(path string) ([]byte, error) {
	f, err := os.Open(path)
	if err != nil {
		return nil, err
	}
	defer f.Close()

	b, err := ioutil.ReadAll(f)
	if err != nil {
		return nil, err
	}

	return b, nil
}
