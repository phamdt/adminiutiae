package main

import (
	"bufio"
	"context"
	"encoding/csv"
	"fmt"
	"log"
	"os"
	"strings"
	"time"

	"github.com/phamdt/adminiutiae/pkg/file"
	"github.com/phamdt/adminiutiae/src/service"
)

func main() {
	outputBaseDir := "/tmp"

	reader := bufio.NewReader(os.Stdin)
	delimiter := byte('\n')

	fmt.Print("Enter your GitHub token: ")
	token, err := reader.ReadString(delimiter)
	if err != nil {
		log.Fatalf("error reading token from stdin: %+v", err)
	}
	token = strings.Trim(token, "\n")

	fmt.Print("Enter the GitHub domain (e.g. https://github.com): ")
	baseGitURL, err := reader.ReadString(delimiter)
	if err != nil {
		log.Fatalf("error reading github domain from stdin: %+v", err)
	}
	baseGitURL = strings.Trim(baseGitURL, "\n")

	fmt.Print("Enter the GitHub org or username to be analyzed: ")
	org, err := reader.ReadString(delimiter)
	if err != nil {
		log.Fatalf("error reading org from stdin: %+v", err)
	}
	org = strings.Trim(org, "\n")

	ctx := context.Background()
	counter := service.NewCounter(ctx, token, baseGitURL)
	header, rows, err := counter.GetGithubLOC(outputBaseDir, org)
	if err != nil {
		log.Fatalf("%+v", err)
		return
	}

	countDir := fmt.Sprintf("counts/%s", org)
	if err := file.CreateDir(countDir); err != nil {
		log.Fatalf("error creating directory: %+v", err)
	}
	t := time.Now()
	prefix := t.Format(time.RFC3339)
	prefix = strings.ReplaceAll(prefix, ":", "")
	fileName := fmt.Sprintf("%s/code_count_%s.csv", countDir, prefix)
	newCsv, err := os.Create(fileName)
	if err != nil {
		panic(err)
	}
	defer newCsv.Close()

	writer := csv.NewWriter(newCsv)
	defer writer.Flush()

	writer.Write(header)
	writer.WriteAll(rows)
}
