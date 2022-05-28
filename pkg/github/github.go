package github

import (
	"context"
	"fmt"

	"github.com/google/go-github/github"
	"golang.org/x/oauth2"
)

func NewClient(token, baseGitURL string, ctx context.Context) *github.Client {
	ts := oauth2.StaticTokenSource(
		&oauth2.Token{AccessToken: token},
	)
	tc := oauth2.NewClient(ctx, ts)
	client, _ := github.NewEnterpriseClient(fmt.Sprintf("%s/api/v3", baseGitURL), "", tc)

	return client
}
