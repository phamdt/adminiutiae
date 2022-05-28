package controllers

import (
	"github.com/gin-gonic/gin"
	mw "github.com/phamdt/adminiutiae/src/controllers/middleware"
)

func GetRouter() *gin.Engine {
	r := gin.Default()
	r.RedirectTrailingSlash = true

	r.Use(mw.HasBasicAuth)

	codeCountCtrl := CodeCountController{}
	r.POST("/github/:org/code/counts", codeCountCtrl.Create)

	return r
}
