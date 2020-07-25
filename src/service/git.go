package service

import (
	"os"

	"github.com/go-git/go-git/v5"
	ghttp "github.com/go-git/go-git/v5/plumbing/transport/http"
	"github.com/pkg/errors"
)

// DownloadRepo uses go-git to download the git repo using the clone URL. If
// you can figure out how to do this with go-github, we can remove the dependency
func DownloadRepo(destinationPath, token, cloneURL string) (*git.Repository, error) {
	repo, err := git.PlainClone(destinationPath, false, &git.CloneOptions{
		Auth: &ghttp.BasicAuth{
			Username: "anything",
			Password: token,
		},
		URL:      cloneURL,
		Progress: os.Stdout,
	})
	if err != nil {
		return nil, errors.WithStack(err)
	}
	return repo, nil
}
