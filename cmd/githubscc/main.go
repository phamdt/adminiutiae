package main

import (
	"bufio"
	"context"
	"encoding/csv"
	"fmt"
	"log"
	"os"
	"strings"

	"github.com/phamdt/adminiutiae/src/file"

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

	if err := file.CreateDir("counts"); err != nil {
		log.Fatalf("error creating directory: %+v", err)
	}

	newCsv, err := os.Create("counts/code_count.csv")
	if err != nil {
		panic(err)
	}
	defer newCsv.Close()

	writer := csv.NewWriter(newCsv)
	defer writer.Flush()

	writer.Write(header)
	writer.WriteAll(rows)
}
