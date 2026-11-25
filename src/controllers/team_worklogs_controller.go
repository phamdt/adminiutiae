package controllers

import (
	"net/http"
	"strconv"

	"github.com/gin-gonic/gin"
	"github.com/phamdt/adminiutiae/pkg/tempo"
)

// TeamWorklogsController exposes methods for team worklogs.
type TeamWorklogsController struct {
	tempo *tempo.Client
}

func NewTeamWorklogsController(tempoClient *tempo.Client) *TeamWorklogsController {
	return &TeamWorklogsController{tempo: tempoClient}
}

func (ctrl *TeamWorklogsController) Index(c *gin.Context) {
	id := c.Param("teamID")
	teamID, _ := strconv.Atoi(id)
	req := &tempo.FindRequest{TeamID: []int{teamID}}
	res, err := ctrl.tempo.GetLogs(req)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, res)
}