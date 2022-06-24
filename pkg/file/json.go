package file

import (
	"encoding/json"
	"os"
)

func CreateJSONFile(name string, i interface{}) {
	f, _ := os.Create(name)
	defer f.Close()

	b, _ := json.Marshal(i)
	f.Write(b)
}
