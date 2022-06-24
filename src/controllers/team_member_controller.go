package controllers

import (
	"net/http"
	"strconv"

	"github.com/gin-gonic/gin"
	"github.com/phamdt/adminiutiae/pkg/tempo"
)

// TeamMemberController exposes the methods for interacting with the
// RESTful Team resource
type TeamController struct {
	tempo *tempo.Client
}

func NewTeamMemberController(tempo *tempo.Client) *TeamController {
	return &TeamController{tempo}
}

func (ctrl *TeamController) Index(c *gin.Context) {
	id := c.Param("teamID")
	teamID, _ := strconv.Atoi(id)
	res, err := ctrl.tempo.GetMembers(teamID)
	if err != nil {
		c.JSON(http.StatusInternalServerError, err)
		return
	}

	c.JSON(http.StatusOK, res)
}
