package response

import (
	"bytes"
	"encoding/csv"
)

func ToCSV(header []string, rows [][]string) []byte {
	b := &bytes.Buffer{}
	writer := csv.NewWriter(b)
	defer writer.Flush()

	writer.Write(header)
	writer.WriteAll(rows)

	return b.Bytes()
}
