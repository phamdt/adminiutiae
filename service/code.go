package service

import (
	"context"
	"encoding/csv"
	"encoding/json"
	"fmt"
	"io/ioutil"
	"os"
	"os/exec"
	"path/filepath"
	"strconv"
	"strings"

	"github.com/pkg/errors"

	"github.com/boyter/scc/processor"
	"github.com/google/go-github/github"
	"github.com/phamdt/adminiutiae/file"
	"github.com/phamdt/adminiutiae/set"
	"golang.org/x/oauth2"
)

type Counter struct {
	Client     *github.Client
	Token      string
	BaseGitURL string
}

func NewCounter(ctx context.Context, token string, baseGitURL string) Counter {
	ts := oauth2.StaticTokenSource(
		&oauth2.Token{AccessToken: token},
	)
	tc := oauth2.NewClient(ctx, ts)
	client, err := github.NewEnterpriseClient(baseGitURL, "", tc)
	if err != nil {
		panic(errors.WithStack(err))
	}

	return Counter{
		Token:      token,
		BaseGitURL: baseGitURL,
		Client:     client,
	}
}

func (c *Counter) CountGithubLOC(outputBaseDir, org string) error {
	reportDir := fmt.Sprintf("%s/reports/%s", outputBaseDir, org)
	if err := file.CreateDir(reportDir); err != nil {
		return errors.WithStack(err)
	}

	reposDir := fmt.Sprintf("%s/repos", outputBaseDir)
	ctx := context.Background()
	opts := &github.RepositoryListByOrgOptions{
		ListOptions: github.ListOptions{PerPage: 2},
	}

	// list all repositories for the authenticated user
	for {
		repos, res, err := c.Client.Repositories.ListByOrg(ctx, org, opts)
		if err != nil {
			return errors.WithStack(err)
		}
		defer res.Body.Close()

		for _, r := range repos {
			if *r.Archived {
				continue
			}

			url := r.GetCloneURL()
			fullName := *r.FullName
			path := filepath.Join(reposDir, fullName)
			if file.DirExists(path) {
				os.RemoveAll(path)
			}

			_, err := DownloadRepo(path, c.Token, url)
			if err != nil {
				return errors.WithStack(err)
			}

			name := *r.Name
			dest := fmt.Sprintf("%s/%s.json", reportDir, name)
			_, err = RunSCC(path, dest)
			if err != nil {
				return errors.WithStack(err)
			}
		}
		if res.NextPage == 0 {
			break
		}
		opts.Page = res.NextPage
	}
	languageSet := set.NewStringSet()
	header := []string{"Org", "Name", "Git Url"}
	var rows [][]string
	file.IterateDirectory(reportDir, func(reportFileName string) error {
		// iterate over files create a slice of strings
		reportPath := filepath.Join(reportDir, reportFileName)
		b, err := file.GetFileBytes(reportPath)
		if err != nil {
			return errors.WithStack(err)
		}

		// get language summary
		var summaries []processor.LanguageSummary
		if err := json.Unmarshal(b, &summaries); err != nil {
			return errors.WithStack(err)
		}
		name := strings.Split(reportFileName, ".")[0]
		repoURL := filepath.Join(c.BaseGitURL, org, name)
		row := []string{org, name, repoURL}
		counts := ExtractLanguageCounts(languageSet, summaries)
		row = append(row, counts...)
		rows = append(rows, row)

		return nil
	})
	foundLanguages := languageSet.List()
	header = append(header, foundLanguages...)

	newCsv, err := os.Create("code-count.csv")
	if err != nil {
		return errors.WithStack(err)
	}
	defer newCsv.Close()

	writer := csv.NewWriter(newCsv)
	defer writer.Flush()

	writer.Write(header)
	writer.WriteAll(rows)

	// cleanup after ourselves
	os.RemoveAll(reportDir)
	os.RemoveAll(reposDir)

	return nil
}

func ExtractLanguageCounts(languageSet set.StringSet, summaries []processor.LanguageSummary) []string {
	localSet := set.NewSummarySet()
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
			s, _ := localSet.GetSummaryMeta(language)
			count := strconv.FormatInt(s.Code, 10)
			counts = append(counts, count)
		} else {
			// add empty string
			counts = append(counts, "")
		}
	}
	return counts
}

// RunSCC executes the scc binary. This means you must ensure that https://github.com/boyter/scc is in the path
func RunSCC(src string, dest string) ([]byte, error) {
	command := exec.Command("scc", "-o", dest, "-f", "json", src)
	return runCommand(command)
}

func runCommand(command *exec.Cmd) ([]byte, error) {
	stderr, err := command.StderrPipe()
	if err != nil {
		return nil, errors.WithStack(err)
	}
	stdOut, err := command.StdoutPipe()
	if err != nil {
		return nil, errors.WithStack(err)
	}

	if err := command.Start(); err != nil {
		return nil, errors.WithStack(err)
	}
	_, err = ioutil.ReadAll(stderr)
	if err != nil {
		return nil, errors.WithStack(err)
	}

	stdOutput, err := ioutil.ReadAll(stdOut)
	if err != nil {
		return nil, errors.WithStack(err)
	}

	if err := command.Wait(); err != nil {
		return nil, errors.WithStack(err)
	}

	return stdOutput, nil
}