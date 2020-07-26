package service

import (
	"context"
	"encoding/json"
	"fmt"
	"io/ioutil"
	"log"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"sync"

	"github.com/pkg/errors"

	"github.com/google/go-github/github"
	"github.com/phamdt/adminiutiae/src/file"
	"github.com/phamdt/adminiutiae/src/set"
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
	client, err := github.NewEnterpriseClient(fmt.Sprintf("%s/api/v3", baseGitURL), "", tc)
	if err != nil {
		panic(errors.WithStack(err))
	}

	return Counter{
		Token:      token,
		BaseGitURL: baseGitURL,
		Client:     client,
	}
}

func (c *Counter) GetGithubLOC(outputBaseDir, org string) ([]string, [][]string, error) {
	reportDir := fmt.Sprintf("%s/reports/%s", outputBaseDir, org)
	reposDir := fmt.Sprintf("%s/repos/%s", outputBaseDir, org)

	// remember to clean up after ourselves
	defer func() {
		os.RemoveAll(reportDir)
		os.RemoveAll(reposDir)
	}()
	if err := file.CreateDir(reportDir); err != nil {
		return []string{}, [][]string{}, errors.WithStack(err)
	}

	ctx := context.Background()
	// TODO: make env vars
	opts := &github.RepositoryListByOrgOptions{
		ListOptions: github.ListOptions{PerPage: 1},
	}

	// list all repositories for the authenticated user
	for {
		repos, res, err := c.Client.Repositories.ListByOrg(ctx, org, opts)
		if err != nil {
			return []string{}, [][]string{}, errors.WithStack(err)
		}
		defer res.Body.Close()

		var repoGroup sync.WaitGroup
		repoGroup.Add(len(repos))

		for _, r := range repos {
			go func(r *github.Repository) {
				defer repoGroup.Done()

				// first conditional is a hack to make tests work
				// the second is because for now we assume we don't care about
				// archived repos
				if r.Archived != nil && *r.Archived {
					return
				}

				url := r.GetCloneURL()
				fullName := *r.FullName
				path := filepath.Join(reposDir, fullName)
				_, err := DownloadRepo(path, c.Token, url)
				if err != nil {
					log.Println(err.Error(), url)
				}
				log.Println("finished downloading", fullName)
			}(r)
		}
		repoGroup.Wait()

		if res.NextPage == 0 {
			break
		}
		opts.Page = res.NextPage
	}

	orgDir := filepath.Join(reposDir, org)
	err := file.IterateDirectory(orgDir, func(name string) error {
		log.Println("preparing to analyze", name)

		dest := fmt.Sprintf("%s/%s.json", reportDir, name)
		path := filepath.Join(orgDir, name)
		_, err := RunSCC(path, dest)
		if err != nil {
			return errors.WithStack(err)
		}
		repoDir := filepath.Join(reposDir, name)
		os.RemoveAll(repoDir)
		log.Println("removed", repoDir)
		return nil
	})

	if err != nil {
		return []string{}, [][]string{}, errors.WithStack(err)
	}

	languageSet := set.NewStringSet()
	header := GetDefaultHeaders()
	var rows [][]string

	err = file.IterateDirectory(reportDir, func(reportFileName string) error {
		// iterate over files create a slice of strings
		reportPath := filepath.Join(reportDir, reportFileName)
		b, err := file.GetFileBytes(reportPath)
		if err != nil {
			return errors.WithStack(err)
		}

		log.Println("preparing to aggregate data from", reportPath)
		// get language summary
		var summaries []LanguageSummary
		if err := json.Unmarshal(b, &summaries); err != nil {
			return errors.WithStack(err)
		}

		name := strings.Split(reportFileName, ".")[0]
		repoURL := filepath.Join(c.BaseGitURL, org, name)
		row := []string{org, name, repoURL}
		counts := ExtractLanguageCounts(&languageSet, summaries)
		row = append(row, counts...)
		rows = append(rows, row)

		return nil
	})
	if err != nil {
		log.Println(err.Error())
		return []string{}, [][]string{}, errors.WithStack(err)
	}

	foundLanguages := languageSet.List()
	header = append(header, foundLanguages...)
	return header, rows, nil
}

func GetDefaultHeaders() []string {
	return []string{"Org", "Name", "Git Url"}
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
